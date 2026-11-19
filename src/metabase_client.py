import os
import re
import time
import json
import logging
import requests
import pandas as pd
from typing import Optional, Dict, Any, List

logger = logging.getLogger("metabase_client")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'metabase_config.json')

def load_metabase_config() -> Dict[str, Any]:
    """
    Loads Metabase connection configuration from metabase_config.json or environment variables.
    """
    cfg = {
        "metabase_url": os.getenv("METABASE_URL", "").rstrip("/"),
        "card_id": os.getenv("METABASE_CARD_ID", ""),
        "session_token": os.getenv("METABASE_SESSION_TOKEN", ""),
        "email_parameter_id": os.getenv("METABASE_EMAIL_PARAM_ID", ""),
        "api_key": os.getenv("METABASE_API_KEY", ""),
        "public_uuid": os.getenv("METABASE_PUBLIC_UUID", ""),
        "username": os.getenv("METABASE_USERNAME", ""),
        "password": os.getenv("METABASE_PASSWORD", ""),
        "timeout_seconds": int(os.getenv("METABASE_TIMEOUT", "30"))
    }
    
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                disk_cfg = json.load(f)
                for k, v in disk_cfg.items():
                    if v and not str(v).startswith("https://metabase.yourcompany"):
                        cfg[k] = v
        except Exception as e:
            logger.warning(f"Failed to read metabase_config.json: {e}")
            
    return cfg

def is_metabase_configured() -> bool:
    """
    Checks whether valid Metabase connection parameters have been provided.
    """
    cfg = load_metabase_config()
    url = cfg.get("metabase_url", "")
    if not url or "yourcompany" in url:
        return False
    return bool(cfg.get("public_uuid") or (cfg.get("card_id") and (cfg.get("session_token") or cfg.get("api_key") or cfg.get("username"))))

def get_session_token(base_url: str, username: str, password: str, timeout: int = 20) -> Optional[str]:
    """
    Obtains a Metabase session token via username and password.
    """
    try:
        url = f"{base_url}/api/session"
        res = requests.post(url, json={"username": username, "password": password}, timeout=timeout)
        if res.status_code == 200:
            return res.json().get("id")
    except Exception as e:
        logger.error(f"Metabase session authentication failed: {e}")
    return None


def _refresh_and_persist_token() -> Optional[str]:
    """
    Auto-renews the Metabase session token using stored username+password
    and persists the new token back to metabase_config.json so it survives restarts.
    Returns the new token or None if credentials are missing / login fails.
    """
    cfg = load_metabase_config()
    base_url = cfg.get("metabase_url", "").rstrip("/")
    username = cfg.get("username", "").strip()
    password = cfg.get("password", "").strip()

    if not username or not password:
        logger.warning("Cannot auto-renew Metabase token: username/password not set in metabase_config.json.")
        return None

    logger.info("Metabase session token expired — auto-renewing via username/password login...")
    new_token = get_session_token(base_url, username, password)
    if not new_token:
        logger.error("Auto-renewal of Metabase session token failed.")
        return None

    # Persist new token to disk so it survives server restarts
    try:
        disk_cfg = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                disk_cfg = json.load(f)
        disk_cfg["session_token"] = new_token
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(disk_cfg, f, indent=2)
        logger.info("New Metabase session token persisted to metabase_config.json.")
    except Exception as e:
        logger.warning(f"Could not persist new Metabase token to disk: {e}")

    return new_token

import time
from threading import Lock

# In-memory TTL cache to protect Metabase from request spikes by 100+ concurrent users
_MB_CACHE_LOCK = Lock()
_MB_DF_CACHE: Optional[pd.DataFrame] = None
_MB_DF_CACHE_TIMESTAMP: float = 0.0
_MB_LEAD_CACHE: Dict[str, Any] = {}
_MB_CACHE_TTL_SECONDS: int = int(os.getenv("METABASE_CACHE_TTL_SECONDS", "900"))  # Default 15 minutes (900 seconds)

def clear_metabase_cache():
    """Manually invalidates the in-memory Metabase caches."""
    global _MB_DF_CACHE, _MB_DF_CACHE_TIMESTAMP, _MB_LEAD_CACHE
    with _MB_CACHE_LOCK:
        _MB_DF_CACHE = None
        _MB_DF_CACHE_TIMESTAMP = 0.0
        _MB_LEAD_CACHE.clear()

def fetch_leads_from_metabase(force_refresh: bool = False) -> pd.DataFrame:
    """
    Fetches the full leads dataset from the configured Metabase Question/Card.
    Cached for 15 minutes by default to prevent rate limits across concurrent users.
    """
    global _MB_DF_CACHE, _MB_DF_CACHE_TIMESTAMP
    now = time.time()
    
    if not force_refresh:
        with _MB_CACHE_LOCK:
            if _MB_DF_CACHE is not None and (now - _MB_DF_CACHE_TIMESTAMP) < _MB_CACHE_TTL_SECONDS:
                return _MB_DF_CACHE.copy()
    cfg = load_metabase_config()
    base_url = cfg.get("metabase_url", "").rstrip("/")
    api_key = cfg.get("api_key", "").strip()
    session_token = cfg.get("session_token", "").strip()
    card_id = cfg.get("card_id")
    public_uuid = cfg.get("public_uuid", "").strip()
    username = cfg.get("username", "").strip()
    password = cfg.get("password", "").strip()
    timeout = cfg.get("timeout_seconds", 30)

    if not base_url or "yourcompany" in base_url:
        raise ValueError("Metabase URL is not configured. Please update metabase_config.json with your Metabase URL.")

    # 1. Public Card Link (Zero authentication required if Public Sharing is enabled on Metabase)
    df_result = None
    if public_uuid:
        url = f"{base_url}/api/public/card/{public_uuid}/query/json"
        res = requests.get(url, timeout=timeout)
        res.raise_for_status()
        data = res.json()
        df_result = pd.DataFrame(data)

    # 2. Authenticated Session Token or API Key Endpoint
    elif (session_token or (username and password)) and card_id:
        url = f"{base_url}/api/card/{card_id}/query"
        token = session_token
        
        # Try up to 2 times (with token auto-renewal if 401 Unauthorized occurs)
        for attempt in range(2):
            if not token and username and password:
                token = _refresh_and_persist_token()
            if not token:
                raise PermissionError("Failed to obtain Metabase session token.")

            headers = {
                "X-Metabase-Session": token,
                "Content-Type": "application/json"
            }
            res = requests.post(url, headers=headers, json={}, timeout=timeout)
            if res.status_code in (401, 403) and attempt == 0 and username and password:
                logger.info("Metabase bulk query returned 401/403. Auto-renewing session token...")
                token = _refresh_and_persist_token()
                continue
            res.raise_for_status()
            data = res.json()
            rows = data.get("data", {}).get("rows", [])
            cols = data.get("data", {}).get("cols", [])
            col_names = [col.get("display_name", col.get("name", "unknown")) for col in cols]
            df_result = pd.DataFrame(rows, columns=col_names)
            break

    elif api_key and card_id:
        url = f"{base_url}/api/card/{card_id}/query"
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        res = requests.post(url, headers=headers, json={}, timeout=timeout)
        res.raise_for_status()
        data = res.json()
        rows = data.get("data", {}).get("rows", [])
        cols = data.get("data", {}).get("cols", [])
        col_names = [col.get("display_name", col.get("name", "unknown")) for col in cols]
        df_result = pd.DataFrame(rows, columns=col_names)
    else:
        raise ValueError("Incomplete Metabase credentials. Set 'public_uuid' OR ('card_id' + 'api_key') in metabase_config.json.")

    if df_result is not None:
        with _MB_CACHE_LOCK:
            _MB_DF_CACHE = df_result
            _MB_DF_CACHE_TIMESTAMP = time.time()
        return df_result.copy()

    return pd.DataFrame()

USE_CARD_LOOKUP = os.getenv("METABASE_USE_CARD_LOOKUP", "0") == "1"

# When one email has several records, keep the one with the most profile fields filled in.
# The signup date only says when the person entered our data, so it is not a signal: it is used last, purely to make the choice repeatable.
_COMPLETENESS_SQL = (
    "(case when role is not null and trim(role) <> '' then 1 else 0 end"
    " + case when experience is not null and experience > 0 then 1 else 0 end"
    " + case when orgname is not null and trim(orgname) <> '' then 1 else 0 end"
    " + case when orgyear is not null then 1 else 0 end"
    " + case when company_type is not null and trim(company_type) <> '' then 1 else 0 end"
    " + case when program_type is not null and trim(program_type) <> '' then 1 else 0 end)"
)


LOOKUP_COLUMNS = (
    "email, name, phone, orgname, orgyear, experience, role, company_type, program_type, which_bda_team, "
    "test_launched_flag, test_passed_flag, event_name, event_type, attended, attended_before_payment_flag, "
    "signed_up_date, lead_created_at, batch, country_type, landing_page_url, utm_source, utm_medium, "
    "utm_campaign, current_lead_stage, minutes_in_event, event_rank_registraion"
)


class MetabaseUnavailable(Exception):
    """Metabase did not answer (timeout, network or server error). Not the same as 'lead not found'."""


def fetch_lead_by_email_from_metabase(query_str: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    Looks up any specific lead by email, phone, or name from Metabase temp.marketing_mis.
    Enables looking up ANY lead out of the entire database on demand.
    Cached in-memory with a 15-minute TTL.
    """
    if not is_metabase_configured():
        return None

    q_clean = query_str.strip().lower()
    now = time.time()

    # Check lead-specific TTL cache
    if not force_refresh:
        with _MB_CACHE_LOCK:
            if q_clean in _MB_LEAD_CACHE:
                cached_entry = _MB_LEAD_CACHE[q_clean]
                if (now - cached_entry['timestamp']) < _MB_CACHE_TTL_SECONDS:
                    return cached_entry['data'].copy() if cached_entry['data'] else None

    cfg = load_metabase_config()
    base_url = cfg.get("metabase_url", "").rstrip("/")
    card_id = cfg.get("card_id", "28973")
    session_token = cfg.get("session_token", "").strip()
    param_id = cfg.get("email_parameter_id", "2dcd8f80-e4b6-46cf-936b-2102140cb7f2")
    timeout = cfg.get("timeout_seconds", 30)

    REQUIRED_COLS = {
        'email', 'name', 'phone', 'role', 'experience', 'orgname', 'orgyear',
        'company_type', 'education', 'program_type', 'which_bda_team',
        'test_launched_flag', 'test_passed_flag', 'event_name', 'event_type',
        'attended_before_payment_flag', 'duration', 'signed_up_date',
        'lead_created_at', 'lead_score', 'batch', 'platform', 'country_type',
        'event_category', 'landing_page_url', 'utm_source', 'utm_medium', 'utm_campaign',
        'current_lead_stage', 'attended', 'minutes_in_event', 'event_rank_registraion'
    }

    # 1. If it's an email address, first attempt parameterized card query
    is_email = "@" in q_clean
    # The parameterised card is slower than the direct lean query below, so it is opt-in.
    if USE_CARD_LOOKUP and is_email and session_token and card_id:
        for attempt in range(2):
            try:
                url = f"{base_url}/api/card/{card_id}/query"
                headers = {
                    "Content-Type": "application/json",
                    "X-Metabase-Session": session_token
                }
                email_param = {
                    "type": "string/=",
                    "value": [q_clean],
                    "target": ["dimension", ["template-tag", "email"]]
                }
                if param_id:
                    email_param["id"] = param_id
                payload = {"parameters": [email_param]}
                res = requests.post(url, headers=headers, json=payload, timeout=lookup_timeout)
                if res.status_code in (200, 202):
                    lookup_error = None
                    data = res.json()
                    rows = data.get("data", {}).get("rows", [])
                    cols = data.get("data", {}).get("cols", [])
                    col_names = [col.get("display_name", col.get("name", "unknown")) for col in cols]
                    if rows:
                        raw_dict = dict(zip(col_names, rows[0]))
                        filtered_dict = {k: v for k, v in raw_dict.items() if k in REQUIRED_COLS}
                        with _MB_CACHE_LOCK:
                            _MB_LEAD_CACHE[q_clean] = {'data': filtered_dict, 'timestamp': now}
                        return filtered_dict
                    break
                elif res.status_code == 401:
                    if attempt == 0:
                        new_token = _refresh_and_persist_token()
                        if new_token:
                            session_token = new_token
                            continue
                    break
            except Exception as e:
                logger.warning(f"Error querying Card 28973 for '{q_clean}': {e}")
                break

    # 2. Universal On-Demand Search: Direct native query across ANY of the 17M+ rows in temp.marketing_mis
    # Works for ANY email, phone number, or exact name
    clean_digits = "".join(ch for ch in q_clean if ch.isdigit())
    safe_str = re.sub(r"[\\'\";]", "", q_clean).strip()   # quote/backslash/semicolon cannot reach the SQL literal (Redshift treats backslash as an escape)
    
    where_clauses = []
    if is_email:
        where_clauses.append(f"lower(email) = '{safe_str}'")
    if len(clean_digits) >= 10:
        phone_suffix = clean_digits[-10:]
        where_clauses.append(f"phone like '%{phone_suffix}'")
    if not is_email and len(clean_digits) < 10 and len(safe_str) >= 3:
        where_clauses.append(f"lower(name) = '{safe_str}'")

    lookup_error = None
    if where_clauses:
        # Columnar warehouse: selecting only the columns the engine uses roughly halves cold-query time vs `select *`.
        sql = f"select {LOOKUP_COLUMNS} from temp.marketing_mis where ({' or '.join(where_clauses)}) order by {_COMPLETENESS_SQL} desc, signed_up_date desc limit 1"
        lookup_timeout = max(timeout, 90)    # a cold query on the 17M-row table can take longer than 30 seconds
        for attempt in range(2):
            try:
                if not session_token:
                    session_token = _refresh_and_persist_token()
                url = f"{base_url}/api/dataset"
                headers = {
                    "Content-Type": "application/json",
                    "X-Metabase-Session": session_token
                }
                payload = {
                    "database": 5,
                    "type": "native",
                    "native": {"query": sql}
                }
                res = requests.post(url, headers=headers, json=payload, timeout=timeout)
                if res.status_code in (200, 202):
                    data = res.json()
                    rows = data.get("data", {}).get("rows", [])
                    cols = data.get("data", {}).get("cols", [])
                    col_names = [col.get("display_name", col.get("name", "unknown")) for col in cols]
                    if rows:
                        raw_dict = dict(zip(col_names, rows[0]))
                        filtered_dict = {k: v for k, v in raw_dict.items() if k in REQUIRED_COLS}
                        with _MB_CACHE_LOCK:
                            _MB_LEAD_CACHE[q_clean] = {'data': filtered_dict, 'timestamp': now}
                        return filtered_dict
                    break
                elif res.status_code == 401:
                    if attempt == 0:
                        session_token = _refresh_and_persist_token()
                        continue
                    lookup_error = 'Metabase rejected the login (HTTP 401)'
                    break
                else:
                    lookup_error = f'Metabase returned HTTP {res.status_code}'
                    if attempt == 0:
                        continue
                    break
            except Exception as e:
                logger.warning(f"Universal MIS query error for '{q_clean}' (attempt {attempt + 1}): {e}")
                lookup_error = str(e)[:200]
                if attempt == 0:
                    continue          # one retry: the second run is usually fast because the warehouse has warmed up
                break

    # 3. Fallback to loaded cache if available

    # 2. Fallback: Full table search if public or api_key configured
    try:
        df = fetch_leads_from_metabase()
        if not df.empty:
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                email_val = str(row_dict.get('email', row_dict.get('Email', ''))).strip().lower()
                phone_val = str(row_dict.get('phone', row_dict.get('Phone', ''))).strip()
                if q_clean in email_val or q_clean in phone_val:
                    with _MB_CACHE_LOCK:
                        _MB_LEAD_CACHE[q_clean] = {'data': row_dict, 'timestamp': now}
                    return row_dict
    except Exception as e:
        logger.warning(f"Fallback Metabase fetch error: {e}")

    if lookup_error:
        # Metabase did not answer, so we do not know whether the lead exists. Do not cache this as 'not found'.
        raise MetabaseUnavailable(lookup_error)

    # Cache negative result briefly (3 minutes) to avoid repeated hammering on nonexistent emails
    with _MB_CACHE_LOCK:
        _MB_LEAD_CACHE[q_clean] = {'data': None, 'timestamp': now - (_MB_CACHE_TTL_SECONDS - 180)}
    return None


# ==============================================================================================================
# Bulk lookup: many emails at once (used when an uploaded file contains only email addresses)
# ==============================================================================================================
_SAFE_EMAIL = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+$")
SOURCE_DB_ID = int(os.getenv("METABASE_SOURCE_DB_ID", "5"))


def is_safe_email(email: str) -> bool:
    """Only plain email characters are allowed, so an address can never alter the SQL it is placed in."""
    return bool(email) and len(email) <= 254 and bool(_SAFE_EMAIL.match(email))


def export_native_query(sql: str, database: Optional[int] = None, timeout: int = 600) -> List[Dict[str, Any]]:
    """Runs a read-only SQL query through Metabase's export endpoint (no 2,000-row cap) and returns rows as dicts."""
    cfg = load_metabase_config()
    base_url = cfg.get("metabase_url", "").rstrip("/")
    token = (cfg.get("session_token") or "").strip() or _refresh_and_persist_token()
    if not base_url or not token:
        raise PermissionError("Metabase is not configured or could not sign in.")
    body = {"query": json.dumps({"database": database or SOURCE_DB_ID, "type": "native", "native": {"query": sql}})}
    for attempt in range(4):
        res = requests.post(f"{base_url}/api/dataset/json", headers={"X-Metabase-Session": token}, data=body, timeout=timeout)
        if res.status_code in (401, 403) and attempt == 0:
            token = _refresh_and_persist_token() or token
            continue
        if res.status_code in (502, 503, 504) and attempt < 3:
            time.sleep(3 * (attempt + 1))      # a busy warehouse sometimes times out once; retry
            continue
        res.raise_for_status()
        data = res.json()
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(f"Metabase query error: {str(data.get('error'))[:300]}")
        return data
    return []


def fetch_leads_by_emails(emails: List[str], chunk_size: int = 300) -> pd.DataFrame:
    """
    Latest Marketing MIS record for each email (the same record a single lookup would return).
    Emails with no record are simply absent from the result.
    """
    safe = [e for e in dict.fromkeys(emails) if is_safe_email(e)]
    frames = []
    for i in range(0, len(safe), chunk_size):
        chunk = safe[i:i + chunk_size]
        in_list = ",".join("'" + e + "'" for e in chunk)
        sql = (
            f"select {LOOKUP_COLUMNS} from ("
            f"select {LOOKUP_COLUMNS}, row_number() over (partition by lower(email) "
            f"order by {_COMPLETENESS_SQL} desc, signed_up_date desc, lead_created_at desc nulls last) as rn "
            f"from temp.marketing_mis where lower(email) in ({in_list})) where rn = 1"
        )
        rows = export_native_query(sql)
        if rows:
            frames.append(pd.DataFrame(rows))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

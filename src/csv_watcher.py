import os
import io
import re
import json
import logging
import pandas as pd
from typing import Dict, Any, Optional, Set, List
from .evaluator import evaluate_lead_profile
from .lead_store import (
    get_connection,
    init_db,
    save_evaluated_lead,
    find_lead_by_query
)
from .batch_processor import find_col

logger = logging.getLogger("csv_watcher")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DEFAULT_CSV_PATH = os.path.join(DATA_DIR, 'incoming_leads.csv')

# Tracks modification times per CSV file: { file_path: last_mtime }
_file_mtimes: Dict[str, float] = {}
_synced_leads_count: int = 0

def ensure_data_dir_exists():
    """Ensures the data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)

def get_all_csv_paths() -> List[str]:
    """
    Returns absolute paths to all CSV files currently inside the data/ directory,
    plus any file specified in the WATCHED_CSV_PATH environment variable.
    """
    ensure_data_dir_exists()
    csv_paths = []
    
    # Check explicit env variable first
    env_path = os.environ.get("WATCHED_CSV_PATH")
    if env_path and os.path.exists(env_path) and env_path.lower().endswith('.csv'):
        csv_paths.append(os.path.abspath(env_path))
        
    # Check all CSV files in data/
    if os.path.exists(DATA_DIR):
        for fname in os.listdir(DATA_DIR):
            if fname.lower().endswith('.csv'):
                full_p = os.path.abspath(os.path.join(DATA_DIR, fname))
                if full_p not in csv_paths:
                    csv_paths.append(full_p)
                    
    return csv_paths

def get_active_csv_path() -> str:
    """Returns the primary active CSV path (for backward compatibility)."""
    all_csvs = get_all_csv_paths()
    if all_csvs:
        # Prioritize files containing 'dummy_leads' or 'incoming'
        for p in all_csvs:
            if 'dummy_leads' in os.path.basename(p).lower():
                return p
        for p in all_csvs:
            if 'incoming' in os.path.basename(p).lower():
                return p
        return all_csvs[0]
    return DEFAULT_CSV_PATH

WATCHED_CSV_PATH = get_active_csv_path()

def get_known_emails() -> Set[str]:
    """Returns the set of lower-cased emails already present in SQLite."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email_lower FROM leads WHERE email_lower IS NOT NULL AND email_lower != '';")
    rows = cursor.fetchall()
    conn.close()
    return {r['email_lower'] for r in rows if r['email_lower']}

def get_watched_csv_status() -> Dict[str, Any]:
    """Returns status and metadata for all watched CSV files in data/."""
    all_csvs = get_all_csv_paths()
    files_info = []
    for p in all_csvs:
        exists = os.path.exists(p)
        mtime = os.path.getmtime(p) if exists else 0.0
        size = os.path.getsize(p) if exists else 0
        files_info.append({
            "filename": os.path.basename(p),
            "full_path": p,
            "exists": exists,
            "last_modified": mtime,
            "size_bytes": size,
            "last_synced_mtime": _file_mtimes.get(p, 0.0)
        })
    return {
        "data_directory": DATA_DIR,
        "total_csv_files_found": len(all_csvs),
        "files": files_info,
        "total_synced_leads": _synced_leads_count
    }

def sync_single_csv_file(file_path: str, force: bool = False, memory_cache_ref: Optional[list] = None) -> int:
    """
    Reads a single CSV file, detects any new rows not yet in the database,
    evaluates them via the engine, and saves to SQLite and memory cache.
    Returns count of newly synced leads.
    """
    global _file_mtimes, _synced_leads_count

    if not os.path.exists(file_path):
        return 0

    current_mtime = os.path.getmtime(file_path)
    last_mtime = _file_mtimes.get(file_path, 0.0)

    # Skip if unchanged and force is False
    if not force and current_mtime <= last_mtime and last_mtime > 0:
        return 0

    # Safe multi-encoding read with on_bad_lines skip
    df = None
    for enc in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv(file_path, encoding=enc, on_bad_lines='skip', low_memory=False)
            break
        except Exception:
            try:
                df = pd.read_csv(file_path, encoding=enc, engine='python', on_bad_lines='skip')
                break
            except Exception:
                continue

    if df is None or df.empty:
        _file_mtimes[file_path] = current_mtime
        return 0

    # Column mapping using fuzzy matcher
    col_lead_id = find_col(df, ['lead_id', 'lead id', 'id', 'candidate_id'])
    col_name = find_col(df, ['full_name', 'name', 'candidate_name', 'student_name', 'lead_name'])
    col_email = find_col(df, ['email', 'email id', 'lead email', 'contact email'])
    col_phone = find_col(df, ['phone', 'contact', 'mobile', 'phone number'])
    col_role = find_col(df, ['role', 'current role', 'designation', 'job title', 'profile'])
    col_exp = find_col(df, ['experience', 'yoe', 'total experience', 'work experience', 'exp'])
    col_edu = find_col(df, ['education', 'degree', 'qualification', 'highest_qualification', 'stream'])
    col_company = find_col(df, ['company_type', 'company type', 'industry', 'sector'])
    col_prev_org = find_col(df, ['previous org name', 'organization', 'company_name', 'company', 'employer'])
    col_prog = find_col(df, ['program', 'inbound program', 'current program', 'course'])
    col_set_status = find_col(df, ['set_status', 'sat_status', 'diagnostic set status', 'diagnostic sat status', 'test_launched_flag'])
    col_set_score = find_col(df, ['set_score', 'sat_score', 'diagnostic set score', 'diagnostic sat score'])
    col_event = find_col(df, ['event_name', 'event', 'webinar'])
    col_attended = find_col(df, ['attended', 'is_attended', 'webinar_attended'])
    col_goal = find_col(df, ['goal', 'current_goal', 'career_goal'])
    col_coding = find_col(df, ['coding background', 'coding_background'])

    known_emails = get_known_emails()
    new_records = []
    file_basename = os.path.basename(file_path)

    for idx, row in df.iterrows():
        raw_email = str(row.get(col_email, '') if col_email else '').strip()
        email_clean = raw_email.lower()
        if not email_clean or email_clean in ['nan', 'none', 'null']:
            continue   # no real email: skip (never fabricate one)

        # Skip if already evaluated in database (unless forced)
        if email_clean in known_emails and not force:
            continue

        raw_name = str(row.get(col_name, 'Prospective Learner') if col_name else 'Prospective Learner').strip()
        raw_phone = str(row.get(col_phone, 'N/A') if col_phone else 'N/A').strip()
        raw_role = str(row.get(col_role, 'General Tech Professional') if col_role else 'General Tech Professional').strip()
        raw_exp = str(row.get(col_exp, '2 years') if col_exp else '2 years').strip()
        raw_edu = str(row.get(col_edu, 'Graduated / Degree') if col_edu else 'Graduated / Degree').strip()
        raw_company = str(row.get(col_company, 'IT Services / Technology') if col_company else 'IT Services / Technology').strip()
        raw_prev_org = str(row.get(col_prev_org, 'Current Company') if col_prev_org else 'Current Company').strip()
        raw_prog = str(row.get(col_prog, 'Academy') if col_prog else 'Academy').strip()
        raw_set_status = str(row.get(col_set_status, 'SET Not Attempted') if col_set_status else 'SET Not Attempted').strip()
        raw_set_score = str(row.get(col_set_score, 'N/A') if col_set_score else 'N/A').strip()
        raw_goal = str(row.get(col_goal, '') if col_goal else '').strip()

        lead_dict = {
            'name': raw_name if raw_name != 'nan' else 'Prospective Learner',
            'email': raw_email,
            'phone': raw_phone if raw_phone != 'nan' else 'N/A',
            'role': raw_role if raw_role != 'nan' else 'General Tech Professional',
            'experience': raw_exp if raw_exp != 'nan' else '2 years',
            'education': raw_edu if raw_edu != 'nan' else 'Graduated / Degree',
            'company type': raw_company if raw_company != 'nan' else 'IT Services / Technology',
            'previous org name': raw_prev_org if raw_prev_org != 'nan' else 'Current Company',
            'program': raw_prog if raw_prog != 'nan' else 'Academy',
            'set_status': raw_set_status if raw_set_status != 'nan' else 'SET Not Attempted',
            'set_score': raw_set_score if raw_set_score != 'nan' else 'N/A',
            'sat_status': raw_set_status if raw_set_status != 'nan' else 'SET Not Attempted',
            'sat_score': raw_set_score if raw_set_score != 'nan' else 'N/A'
        }

        # Run recommendation engine
        eval_res = evaluate_lead_profile(lead_dict)

        # Preserve lead_id from CSV if present
        csv_lead_id = str(row.get(col_lead_id, '') if col_lead_id else '').strip()
        if csv_lead_id and csv_lead_id.lower() not in ['nan', 'none', 'null', 'n/a', '']:
            lead_id = csv_lead_id
        else:
            lead_id = ""
        eval_res['lead_id'] = lead_id
        eval_res['_uid'] = lead_id or email_clean

        # Touchpoint metadata
        event_name = str(row.get(col_event, f"CSV: {file_basename}") if col_event else f"CSV: {file_basename}")
        attended_val = str(row.get(col_attended, 'Registered') if col_attended else 'Registered')
        summary_str = f"Goal: {raw_goal}" if (raw_goal and raw_goal != 'nan') else f"File: {file_basename}"

        eval_res['touchpoints'] = {
            'summary': summary_str,
            'event_name': event_name if event_name != 'nan' else f"CSV File: {file_basename}",
            'attended': attended_val if attended_val != 'nan' else 'Yes',
            'duration': "N/A",
            'sat_status': lead_dict['sat_status'],
            'sat_score': lead_dict['sat_score'],
            'set_status': lead_dict['set_status'],
            'set_score': lead_dict['set_score'],
            'channel': f"Data Folder CSV ({file_basename})",
            'campaign': "Live Folder Watcher",
            'platform': "Local CSV Stream",
            'geography': "India / General",
            'signup_date': "Live Just Now",
            'lead_score': "Hot (CSV Stream)",
            'landing_page': "https://www.scaler.com"
        }

        # Save to SQLite database
        save_evaluated_lead(eval_res, source=f"CSV: {file_basename}")
        known_emails.add(email_clean)
        new_records.append(eval_res)

        # Update in-memory cache
        if memory_cache_ref is not None:
            if not any(l.get('lead_id') == lead_id for l in memory_cache_ref):
                memory_cache_ref.insert(0, eval_res)

    _file_mtimes[file_path] = current_mtime
    _synced_leads_count += len(new_records)
    return len(new_records)

def sync_all_csvs(force: bool = False, memory_cache_ref: Optional[list] = None) -> Dict[str, Any]:
    """
    Scans ALL .csv files inside the data/ folder.
    Evaluates newly added rows or newly added CSV files automatically.
    """
    all_csvs = get_all_csv_paths()
    total_new_synced = 0
    synced_files_summary = []

    for p in all_csvs:
        try:
            new_count = sync_single_csv_file(p, force=force, memory_cache_ref=memory_cache_ref)
            total_new_synced += new_count
            if new_count > 0:
                synced_files_summary.append({
                    "file": os.path.basename(p),
                    "new_leads": new_count
                })
        except Exception as err:
            logger.error(f"Error syncing {p}: {err}")

    return {
        "status": "success",
        "data_dir": DATA_DIR,
        "total_csv_files": len(all_csvs),
        "new_leads_synced": total_new_synced,
        "synced_files": synced_files_summary,
        "total_synced_so_far": _synced_leads_count
    }

# Backward compatibility alias
sync_watched_csv = sync_all_csvs

def append_lead_to_csv(lead_row: Dict[str, Any], target_csv: Optional[str] = None) -> Dict[str, Any]:
    """
    Appends a new lead record to a CSV file in data/ and triggers an immediate sync.
    """
    ensure_data_dir_exists()
    csv_path = target_csv or get_active_csv_path()
    df_new = pd.DataFrame([lead_row])

    try:
        if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
            df_existing = pd.read_csv(csv_path, on_bad_lines='skip', low_memory=False)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_csv(csv_path, index=False)
        else:
            df_new.to_csv(csv_path, index=False)
    except Exception:
        has_header = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
        df_new.to_csv(csv_path, mode='a', header=not has_header, index=False)

    sync_result = sync_all_csvs(force=True)
    return {
        "status": "success",
        "target_file": csv_path,
        "appended": lead_row,
        "sync_result": sync_result
    }

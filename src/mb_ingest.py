"""
All-batch Metabase ingestion + evaluation.

Why this exists
---------------
The card-based sync (/api/metabase/sync) can only return the first 2,000 rows of card 28973, which is a single
historical slice. The real source is the warehouse table `temp.marketing_mis` (~17.9M rows, ~4.4M distinct leads,
60+ batches). This module pulls EVERY batch through Metabase's export endpoint (not subject to the 2,000-row cap),
keeps ONE row per lead (their most recent record), stores the raw inputs compactly in SQLite, and evaluates them
into a small per-lead summary. Full evaluations (scripts, curriculum, ~8 KB each) are regenerated on demand, so
the database stays small.

Flow:  list_batches() -> ingest (per batch, newest first, resumable) -> evaluate (chunked) -> summary / browse.
"""
import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from fastapi import APIRouter, HTTPException

from .batch_processor import process_leads_dataframe
from .metabase_client import _COMPLETENESS_SQL
from .lead_store import get_connection
from .matrix_engine import canonical_prog_key
from .metabase_client import (
    _refresh_and_persist_token,
    is_metabase_configured,
    load_metabase_config,
)

SOURCE_TABLE = os.getenv("METABASE_SOURCE_TABLE", "temp.marketing_mis")
SOURCE_DB_ID = int(os.getenv("METABASE_SOURCE_DB_ID", "5"))
PAUSE_BETWEEN_BATCHES_S = float(os.getenv("METABASE_INGEST_PAUSE_S", "1.0"))
EVAL_CHUNK = int(os.getenv("EVAL_CHUNK_SIZE", "10000"))

# Columns the evaluator / batch processor can use. Only those that exist in the table are selected.
WANTED_COLUMNS = [
    "email", "name", "phone", "orgname", "orgyear", "experience", "role", "company_type", "education",
    "program_type", "which_bda_team", "assigned_bda_program", "paid_for", "first_payment_done",
    "test_launched_flag", "test_passed_flag", "event_name", "event_type", "attended",
    "attended_before_payment_flag", "signed_up_date", "lead_created_at", "batch", "utm_source",
    "utm_medium", "utm_campaign", "current_lead_stage", "country_type", "eligible_flag",
]

router = APIRouter()
_job_lock = threading.Lock()
_job: Dict[str, Any] = {"running": False, "kind": None, "message": "idle", "done": 0, "total": 0, "error": None}
_available_columns: Optional[List[str]] = None


# ---------------------------------------------------------------------------------------------
# Metabase access
# ---------------------------------------------------------------------------------------------
def _token() -> str:
    cfg = load_metabase_config()
    tok = (cfg.get("session_token") or "").strip() or _refresh_and_persist_token()
    if not tok:
        raise PermissionError("Could not obtain a Metabase session token.")
    return tok


def _export_json(sql: str, timeout: int = 600) -> List[Dict[str, Any]]:
    """Runs a native SQL query through the export endpoint (no 2,000-row cap) and returns rows as dicts."""
    cfg = load_metabase_config()
    base = cfg["metabase_url"].rstrip("/")
    body = {"query": json.dumps({"database": SOURCE_DB_ID, "type": "native", "native": {"query": sql}})}
    token = _token()
    for attempt in range(2):
        res = requests.post(
            f"{base}/api/dataset/json", headers={"X-Metabase-Session": token}, data=body, timeout=timeout
        )
        if res.status_code in (401, 403) and attempt == 0:
            token = _refresh_and_persist_token() or token
            continue
        res.raise_for_status()
        data = res.json()
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(f"Metabase query error: {str(data.get('error'))[:300]}")
        return data
    return []


_BATCH_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def _valid_batch(name: str) -> str:
    if not _BATCH_RE.match(str(name)):
        raise ValueError(f"Invalid batch name: {name!r}")
    return str(name)


def _sql_str(value: str) -> str:
    return "'" + _valid_batch(value) + "'"


def get_available_columns() -> List[str]:
    global _available_columns
    if _available_columns is None:
        rows = _export_json(f"select * from {SOURCE_TABLE} limit 1")
        have = set(rows[0].keys()) if rows else set()
        _available_columns = [c for c in WANTED_COLUMNS if c in have]
    return _available_columns


def list_batches() -> List[Dict[str, Any]]:
    """All batches in the source table, newest first, with row counts."""
    rows = _export_json(
        f"select batch, count(*) as n_rows, max(signed_up_date) as last_signup "
        f"from {SOURCE_TABLE} where batch is not null and batch <> '' group by batch order by max(signed_up_date) desc"
    )
    return [{"batch": r["batch"], "rows": int(r["n_rows"]), "last_signup": r["last_signup"]} for r in rows]


def fetch_batch_latest_leads(batch: str) -> pd.DataFrame:
    """One row per lead (most recent record within the batch) for every lead in the batch."""
    cols = get_available_columns()
    col_list = ", ".join(cols)
    sql = (
        f"select {col_list} from ("
        f"  select {col_list}, row_number() over ("
        f"    partition by lower(email) order by {_COMPLETENESS_SQL} desc, signed_up_date desc, lead_created_at desc nulls last) as rn "
        f"  from {SOURCE_TABLE} where batch = {_sql_str(batch)} and email is not null and email <> ''"
        f") where rn = 1"
    )
    return pd.DataFrame(_export_json(sql))


# ---------------------------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------------------------
def init_ingest_tables() -> None:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS mb_leads_raw (
            email_lower TEXT PRIMARY KEY, batch TEXT, signed_up_date TEXT, payload TEXT)"""
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_mb_raw_batch ON mb_leads_raw(batch)")
    c.execute(
        """CREATE TABLE IF NOT EXISTS mb_ingest_state (
            batch TEXT PRIMARY KEY, status TEXT, rows_fetched INTEGER, leads_new INTEGER,
            started_at REAL, finished_at REAL, error TEXT)"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS lead_eval_summary (
            email_lower TEXT PRIMARY KEY, batch TEXT, eligible INTEGER, persona_key TEXT, exp_bracket TEXT,
            inbound_program TEXT, rec_program TEXT, rec_track TEXT, rec_refund REAL, rec_cohort INTEGER,
            risk_tag TEXT, conf_tier TEXT, fb_program TEXT, fb_refund REAL, changed_from_inbound INTEGER,
            role_known INTEGER, evaluated_at REAL)"""
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_sum_batch ON lead_eval_summary(batch)")
    conn.commit()
    conn.close()


def _compact_payload(rec: Dict[str, Any]) -> str:
    return json.dumps({k: v for k, v in rec.items() if v not in (None, "", "nan")}, separators=(",", ":"), default=str)


def ingest_batch(batch: str) -> Dict[str, Any]:
    """Fetches one batch and stores each lead the first time it is seen (batches run newest-first, so a lead
    keeps its most recent record)."""
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO mb_ingest_state(batch,status,rows_fetched,leads_new,started_at) VALUES (?,?,?,?,?)",
        (batch, "running", 0, 0, time.time()),
    )
    conn.commit()
    try:
        df = fetch_batch_latest_leads(batch)
        fetched = len(df)
        new = 0
        if fetched:
            records = df.where(pd.notnull(df), None).to_dict("records")
            for i in range(0, len(records), 20000):
                chunk = records[i:i + 20000]
                rows = [
                    (str(r["email"]).strip().lower(), batch, str(r.get("signed_up_date") or ""), _compact_payload(r))
                    for r in chunk if r.get("email")
                ]
                before = conn.total_changes
                conn.executemany("INSERT OR IGNORE INTO mb_leads_raw VALUES (?,?,?,?)", rows)
                new += conn.total_changes - before
                conn.commit()
        conn.execute(
            "UPDATE mb_ingest_state SET status='done', rows_fetched=?, leads_new=?, finished_at=? WHERE batch=?",
            (fetched, new, time.time(), batch),
        )
        conn.commit()
        return {"batch": batch, "rows_fetched": fetched, "leads_new": new}
    except Exception as e:
        conn.execute("UPDATE mb_ingest_state SET status='error', error=?, finished_at=? WHERE batch=?",
                     (str(e)[:500], time.time(), batch))
        conn.commit()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------------------------
# Background jobs
# ---------------------------------------------------------------------------------------------
def _set_job(**kw):
    with _job_lock:
        _job.update(kw)


def _ingest_job(batches: List[str]):
    try:
        _set_job(running=True, kind="ingest", total=len(batches), done=0, error=None, message="starting")
        for i, b in enumerate(batches):
            _set_job(message=f"ingesting {b} ({i + 1}/{len(batches)})")
            r = ingest_batch(b)
            _set_job(done=i + 1, message=f"{b}: {r['rows_fetched']} leads fetched, {r['leads_new']} new")
            time.sleep(PAUSE_BETWEEN_BATCHES_S)
        _set_job(running=False, message="ingest complete")
    except Exception as e:
        _set_job(running=False, error=str(e)[:500], message="ingest failed")


def _summary_row(rec: Dict[str, Any], batch: str, email_lower: str) -> tuple:
    p, pr, fb = rec.get("person", {}), rec.get("primary", {}), rec.get("fallback", {})
    elig = 1 if rec.get("academic_eligibility", {}).get("is_eligible", True) else 0
    inbound = canonical_prog_key(p.get("enquired_program", ""))
    rec_key = canonical_prog_key(pr.get("program", "")) if elig else "INELIGIBLE"
    role = str(p.get("role", ""))
    role_known = 0 if role in ("", "Other", "General Tech Professional", "General Professional / Career Switcher") else 1
    return (
        email_lower, batch, elig, p.get("persona_key"), p.get("normalized_experience"), inbound, rec_key,
        pr.get("track"), pr.get("refund_rate"), pr.get("cohort_size"), pr.get("risk_tag"), pr.get("confidence_tier"),
        canonical_prog_key(fb.get("program", "")), fb.get("refund_rate"),
        1 if (elig and rec_key != inbound) else 0, role_known, time.time(),
    )


def _evaluate_batches(batches: List[str], redo: bool):
    try:
        _set_job(running=True, kind="evaluate", done=0, error=None, message="counting")
        conn = get_connection()
        marks = ",".join("?" * len(batches))
        total = conn.execute(f"SELECT COUNT(*) FROM mb_leads_raw WHERE batch IN ({marks})", batches).fetchone()[0]
        _set_job(total=total)
        done = 0
        for b in batches:
            last = ""
            while True:
                q = ("SELECT r.email_lower, r.payload FROM mb_leads_raw r "
                     + ("" if redo else "LEFT JOIN lead_eval_summary s ON s.email_lower = r.email_lower ")
                     + "WHERE r.batch=? AND r.email_lower>? "
                     + ("" if redo else "AND s.email_lower IS NULL ")
                     + "ORDER BY r.email_lower LIMIT ?")
                args = (b, last, EVAL_CHUNK)
                rows = conn.execute(q, args).fetchall()
                if not rows:
                    break
                df = pd.DataFrame([json.loads(r["payload"]) for r in rows])
                evaluated, _ = process_leads_dataframe(df, include_export_df=False)
                out = []
                for ev in evaluated:
                    em = str(ev.get("person", {}).get("email", "")).strip().lower()
                    if em:
                        out.append(_summary_row(ev, b, em))
                conn.executemany("INSERT OR REPLACE INTO lead_eval_summary VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", out)
                conn.commit()
                last = rows[-1]["email_lower"]
                done += len(rows)
                _set_job(done=done, message=f"evaluating {b}: {done}/{total}")
        conn.close()
        _set_job(running=False, message="evaluation complete")
    except Exception as e:
        _set_job(running=False, error=str(e)[:500], message="evaluation failed")


def _start(target, *args) -> Dict[str, Any]:
    with _job_lock:
        if _job["running"]:
            raise HTTPException(status_code=409, detail=f"A job is already running: {_job['message']}")
        _job.update(running=True)
    threading.Thread(target=target, args=args, daemon=True).start()
    return {"status": "started"}


# ---------------------------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------------------------
@router.get("/api/metabase/batches")
def api_batches():
    """Batches available in Metabase, merged with local ingest state."""
    if not is_metabase_configured():
        raise HTTPException(status_code=400, detail="Metabase is not configured.")
    init_ingest_tables()
    try:
        remote = list_batches()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not list batches: {e}")
    conn = get_connection()
    state = {r["batch"]: dict(r) for r in conn.execute("SELECT * FROM mb_ingest_state")}
    counts = {r[0]: r[1] for r in conn.execute("SELECT batch, COUNT(*) FROM mb_leads_raw GROUP BY batch")}
    evald = {r[0]: r[1] for r in conn.execute("SELECT batch, COUNT(*) FROM lead_eval_summary GROUP BY batch")}
    conn.close()
    for b in remote:
        b["ingest_status"] = state.get(b["batch"], {}).get("status", "not_ingested")
        b["leads_stored"] = counts.get(b["batch"], 0)
        b["leads_evaluated"] = evald.get(b["batch"], 0)
    return {"batches": remote, "total_batches": len(remote)}


@router.post("/api/metabase/ingest")
def api_ingest(batches: Optional[str] = None, max_batches: Optional[int] = None, refetch: bool = False):
    """Pulls leads from Metabase for all batches (default), newest first. Resumable: finished batches are skipped
    unless refetch=true. Use max_batches to run a small first pass."""
    if not is_metabase_configured():
        raise HTTPException(status_code=400, detail="Metabase is not configured.")
    init_ingest_tables()
    try:
        names = [_valid_batch(b.strip()) for b in batches.split(",")] if batches else [b["batch"] for b in list_batches()]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not refetch:
        conn = get_connection()
        done = {r[0] for r in conn.execute("SELECT batch FROM mb_ingest_state WHERE status='done'")}
        conn.close()
        names = [n for n in names if n not in done]
    if max_batches:
        names = names[:max_batches]
    if not names:
        return {"status": "nothing_to_do", "message": "All requested batches are already ingested."}
    res = _start(_ingest_job, names)
    res["batches"] = names
    return res


@router.post("/api/metabase/evaluate")
def api_evaluate(batch: str = "all", redo: bool = False):
    """Evaluates stored leads into the per-lead summary table (persona, recommendation, refund %, risk)."""
    init_ingest_tables()
    conn = get_connection()
    stored = [r[0] for r in conn.execute("SELECT DISTINCT batch FROM mb_leads_raw ORDER BY batch")]
    conn.close()
    try:
        names = stored if batch == "all" else [_valid_batch(batch)]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not stored:
        raise HTTPException(status_code=400, detail="No leads ingested yet. Run /api/metabase/ingest first.")
    res = _start(_evaluate_batches, names, redo)
    res["batches"] = names
    return res


@router.get("/api/metabase/ingest/status")
def api_job_status():
    init_ingest_tables()
    conn = get_connection()
    raw = conn.execute("SELECT COUNT(*) FROM mb_leads_raw").fetchone()[0]
    ev = conn.execute("SELECT COUNT(*) FROM lead_eval_summary").fetchone()[0]
    nb = conn.execute("SELECT COUNT(*) FROM mb_ingest_state WHERE status='done'").fetchone()[0]
    conn.close()
    with _job_lock:
        job = dict(_job)
    return {"job": job, "batches_ingested": nb, "leads_stored": raw, "leads_evaluated": ev}


@router.get("/api/metabase/summary")
def api_summary(batch: str = "all"):
    """Aggregates over evaluated leads: program mix, average refund %, risk tags, how often the recommendation
    differs from the inbound program."""
    init_ingest_tables()
    conn = get_connection()
    where, args = ("", ()) if batch == "all" else ("WHERE batch=?", (batch,))
    def q(sql): return conn.execute(sql.format(w=where), args).fetchall()
    total = q("SELECT COUNT(*) FROM lead_eval_summary {w}")[0][0]
    if not total:
        conn.close()
        return {"batch": batch, "evaluated": 0}
    ew = ("WHERE eligible=1" if not where else where + " AND eligible=1")
    def qe(sql): return conn.execute(sql.format(w=ew), args).fetchall()
    out = {
        "batch": batch, "evaluated": total,
        "eligible": qe("SELECT COUNT(*) FROM lead_eval_summary {w}")[0][0],
        "avg_expected_refund_pct": round(qe("SELECT AVG(rec_refund) FROM lead_eval_summary {w}")[0][0] or 0, 2),
        "recommended_program_mix": {r[0]: r[1] for r in qe("SELECT rec_program, COUNT(*) FROM lead_eval_summary {w} GROUP BY 1 ORDER BY 2 DESC")},
        "inbound_program_mix": {r[0]: r[1] for r in qe("SELECT inbound_program, COUNT(*) FROM lead_eval_summary {w} GROUP BY 1 ORDER BY 2 DESC")},
        "risk_tags": {r[0]: r[1] for r in qe("SELECT risk_tag, COUNT(*) FROM lead_eval_summary {w} GROUP BY 1")},
        "changed_from_inbound": qe("SELECT SUM(changed_from_inbound) FROM lead_eval_summary {w}")[0][0],
        "role_unknown": conn.execute(("SELECT COUNT(*) FROM lead_eval_summary " + ew + " AND role_known=0"), args).fetchone()[0],
        "persona_mix": {r[0]: r[1] for r in qe("SELECT persona_key, COUNT(*) FROM lead_eval_summary {w} GROUP BY 1 ORDER BY 2 DESC")},
        "ineligible": total - qe("SELECT COUNT(*) FROM lead_eval_summary {w}")[0][0],
    }
    conn.close()
    return out


@router.get("/api/metabase/leads")
def api_leads(batch: str, offset: int = 0, limit: int = 100):
    """Browse any ingested batch: returns FULL evaluations (scripts included) for one page of leads."""
    init_ingest_tables()
    limit = max(1, min(limit, 500))
    conn = get_connection()
    rows = conn.execute("SELECT payload FROM mb_leads_raw WHERE batch=? ORDER BY email_lower LIMIT ? OFFSET ?",
                        (batch, limit, offset)).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM mb_leads_raw WHERE batch=?", (batch,)).fetchone()[0]
    conn.close()
    if not rows:
        return {"batch": batch, "total": total, "offset": offset, "returned": 0, "leads": []}
    df = pd.DataFrame([json.loads(r["payload"]) for r in rows])
    evaluated, _ = process_leads_dataframe(df, include_export_df=False)
    return {"batch": batch, "total": total, "offset": offset, "returned": len(evaluated), "leads": evaluated}

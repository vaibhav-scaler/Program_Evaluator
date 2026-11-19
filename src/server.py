import os
import datetime
import io
import json
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from .batch_processor import process_leads_dataframe, find_col
from .evaluator import evaluate_lead_profile
from .market_intelligence import get_all_curricula_catalog
from .lead_store import (
    init_db, save_evaluated_lead, bulk_save_evaluated_leads,
    find_lead_by_query, get_recent_leads, get_total_leads_count, get_connection
)
import asyncio
from starlette.concurrency import run_in_threadpool
from .csv_watcher import (
    sync_watched_csv,
    get_watched_csv_status,
    append_lead_to_csv,
    WATCHED_CSV_PATH
)
from .metabase_client import (
    is_metabase_configured,
    fetch_leads_from_metabase,
    fetch_lead_by_email_from_metabase,
    load_metabase_config,
    MetabaseUnavailable,
    fetch_leads_by_emails,
    is_safe_email,
)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WEB_DIR = os.path.join(BASE_DIR, 'web')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
EXPORT_CSV_PATH = os.path.join(OUTPUT_DIR, 'crm_evaluated_master.csv')

# Initialize SQLite database on startup
init_db()

app = FastAPI(title="Scaler Program Evaluator - Sales Decision Engine")

# Bulk all-batch ingest/evaluation is an offline analysis tool (multi-GB, long-running). It is OFF by default so it
# can never run on a small/free host; enable it only on a machine that has the disk and memory for it.
if os.getenv("ENABLE_BULK_INGEST", "0") == "1":
    from .mb_ingest import router as mb_ingest_router
    app.include_router(mb_ingest_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Initial sync from watched CSV
    try:
        res = sync_watched_csv(force=True, memory_cache_ref=CACHED_LEADS)
        print(f">> Watched CSV Initial Sync: {res.get('new_leads_synced', 0)} new leads loaded from {res.get('file_path')}")
    except Exception as e:
        print(f"Warning during initial CSV watcher sync: {e}")
        
    # Start background polling task (checks every 5 seconds for newly added rows)
    async def poll_watched_csv_loop():
        while True:
            await asyncio.sleep(5)
            try:
                sync_res = sync_watched_csv(force=False, memory_cache_ref=CACHED_LEADS)
                new_count = sync_res.get('new_leads_synced', 0)
                if new_count > 0:
                    print(f">> Watched CSV Update Detected: Auto-evaluated and synced {new_count} new leads!")
            except Exception:
                pass
                
    asyncio.create_task(poll_watched_csv_loop())

@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "scaler-program-evaluator",
        "version": "1.0.0"
    }


@app.get("/api/curriculum-catalog")
async def get_curriculum_catalog_endpoint():
    """Returns the complete official Scaler curriculum track modules catalog."""
    return {
        "status": "success",
        "catalog": get_all_curricula_catalog()
    }

@app.get("/scaler_logo.png")
@app.get("/scaler_logo_full.png")
async def serve_scaler_logo():
    logo_path = os.path.join(WEB_DIR, 'scaler_logo.png')
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo not found")

@app.get("/avatar_male.png")
async def serve_avatar_male():
    avatar_path = os.path.join(WEB_DIR, 'avatar_male.png')
    if os.path.exists(avatar_path):
        return FileResponse(avatar_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Male avatar not found")

@app.get("/avatar_female.png")
async def serve_avatar_female():
    avatar_path = os.path.join(WEB_DIR, 'avatar_female.png')
    if os.path.exists(avatar_path):
        return FileResponse(avatar_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Female avatar not found")

# Global in-memory store of uploaded/evaluated leads (Starts 100% EMPTY)
CACHED_LEADS = []
CACHED_DF = None

class SingleLeadInput(BaseModel):
    name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    role: str
    experience: str
    education: Optional[str] = "Graduated / Degree"
    company_type: Optional[str] = ""
    previous_org: Optional[str] = ""
    previous_org_year: Optional[str] = ""
    program: Optional[str] = "Academy"
    set_score: Optional[str] = None
    set_status: Optional[str] = None
    sat_score: Optional[str] = "N/A"
    sat_status: Optional[str] = "SET Not Attempted"

class CRMWebhookLead(BaseModel):
    lead_id: Optional[str] = None   # the CRM's own lead id, if it sends one
    name: Optional[str] = ""
    email: str
    phone: Optional[str] = ""
    role: Optional[str] = ""
    experience: Optional[str] = ""
    education: Optional[str] = "Graduated / Degree"
    company_type: Optional[str] = ""
    previous_org: Optional[str] = ""
    program: Optional[str] = "Academy"
    event_name: Optional[str] = "Direct CRM Inbound Registration"
    attended: Optional[str] = "Attended"
    duration: Optional[str] = "N/A"
    set_score: Optional[str] = None
    set_status: Optional[str] = None
    sat_score: Optional[str] = "N/A"
    sat_status: Optional[str] = "SET Attempted"
    channel: Optional[str] = "CRM Webhook / Inbound"

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(WEB_DIR, 'index.html')
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Frontend UI not found")
    with open(index_path, 'r', encoding='utf-8') as f:
        return HTMLResponse(
            content=f.read(),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )


# ---------------------------------------------------------------------------------------------
# Bulk upload guardrails (enforced on the server; the browser checks are only a convenience)
# ---------------------------------------------------------------------------------------------
MAX_UPLOAD_ROWS = int(os.getenv("MAX_UPLOAD_ROWS", "10000"))   # ~180 MB peak RAM at 10k rows (measured); 50k rows exceeds 512 MB
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
_REQUIRED_UPLOAD_COLUMNS = {
    'email': ['email', 'email id', 'lead email', 'contact email'],
    'role': ['role', 'current role', 'designation', 'job title', 'title', 'current designation', 'profile'],
}
_EXPERIENCE_COLUMNS = ['experience', 'yoe', 'total experience', 'work experience', 'total work experience', 'years of experience', 'exp']


def _validate_upload_structure(df: pd.DataFrame) -> pd.DataFrame:
    """Drops fully empty rows, then enforces the row limit and the required columns. Raises HTTPException(400)."""
    df = df.dropna(how="all")
    if len(df) == 0:
        raise HTTPException(status_code=400, detail="The file has no data rows.")
    if len(df) > MAX_UPLOAD_ROWS:
        raise HTTPException(
            status_code=400,
            detail=(f"The file has {len(df):,} rows, which is more than the {MAX_UPLOAD_ROWS:,}-row limit per upload. "
                    f"Please split it into files of up to {MAX_UPLOAD_ROWS:,} rows."),
        )
    if find_col(df, _REQUIRED_UPLOAD_COLUMNS['email']) is None:
        found = ", ".join(str(c) for c in list(df.columns)[:15])
        raise HTTPException(
            status_code=400,
            detail=f"Missing required column: email. Columns found in your file: {found}.",
        )
    return df


def _count(n: int, singular: str, plural: Optional[str] = None) -> str:
    return f"{n:,} {singular if n == 1 else (plural or singular + 's')}"


def _upload_warnings(df: pd.DataFrame, stats: Optional[dict] = None) -> list:
    """Non-blocking data-quality notes about the uploaded file, shown to the user after evaluation."""
    warnings = []
    role_col = find_col(df, _REQUIRED_UPLOAD_COLUMNS['role'])
    exp_col = find_col(df, _EXPERIENCE_COLUMNS)
    if stats:
        n = stats.get("no_email", 0)
        if n:
            warnings.append({"code": "rows_without_email", "count": n,
                             "message": f"{_count(n, 'row')} without an email {'was' if n == 1 else 'were'} skipped. Leads are identified by their email."})
        n = stats.get("duplicates", 0)
        if n:
            warnings.append({"code": "duplicate_emails", "count": n,
                             "message": f"{_count(n, 'duplicate email')} {'was' if n == 1 else 'were'} merged. Only the last row for each email is kept."})
    if role_col is not None:
        n = int(df[role_col].astype(str).str.strip().str.lower().isin(["", "nan", "none", "null"]).sum())
        if n:
            warnings.append({"code": "missing_role", "count": n,
                             "message": f"{_count(n, 'row')} {'has' if n == 1 else 'have'} no role, so the recommendation for {'it' if n == 1 else 'them'} is low confidence."})
    if exp_col is not None:
        raw = df[exp_col].astype(str).str.strip()
        plain = raw[raw.str.fullmatch(r"\d+(\.\d+)?")]
        n = int(((plain.astype(float) >= 6) & (plain.astype(float) <= 480)).sum()) if len(plain) else 0
        if n:
            warnings.append({"code": "experience_read_as_months", "count": n,
                             "message": (f"{_count(n, 'row')} {'has' if n == 1 else 'have'} experience written as a plain number of 6 or more, "
                                         f"which is read as months (for example, 8 is 8 months). Write 8 years if you mean years.")})
    return warnings

UPLOAD_CHUNK_ROWS = int(os.getenv("UPLOAD_CHUNK_ROWS", "1000"))
UPLOAD_DISPLAY_LEADS = int(os.getenv("UPLOAD_DISPLAY_LEADS", "2000"))


def _evaluate_upload_in_chunks(df: pd.DataFrame, source_label: str):
    """Evaluates the dataframe chunk by chunk, saving each chunk to SQLite and keeping only the first few leads."""
    display, total = [], len(df)
    for start in range(0, total, UPLOAD_CHUNK_ROWS):
        part = df.iloc[start:start + UPLOAD_CHUNK_ROWS].reset_index(drop=True)
        evaluated, _ = process_leads_dataframe(part, include_export_df=False, index_offset=start)
        for r in evaluated:
            r['source'] = source_label
        try:
            # the first chunk clears the previous upload; later chunks append
            bulk_save_evaluated_leads(evaluated, source=source_label, replace_existing=(start == 0))
        except Exception as db_err:
            print(f"Warning during SQLite persistence: {db_err}")
        if len(display) < UPLOAD_DISPLAY_LEADS:
            display.extend(evaluated[:UPLOAD_DISPLAY_LEADS - len(display)])
        del evaluated, part
    return display, total


# ---------------------------------------------------------------------------------------------------------------
# Email-only uploads: the lead details are fetched from Metabase (background job with progress)
# ---------------------------------------------------------------------------------------------------------------
import threading
import time as _time
import uuid

EMAIL_LOOKUP_CHUNK = int(os.getenv("EMAIL_LOOKUP_CHUNK", "2000"))
_EMAIL_JOBS: dict = {}
_EMAIL_JOBS_LOCK = threading.Lock()


def _run_email_lookup_job(job_id: str, emails: list, filename: str, stats: dict):
    """Looks every email up in Metabase, evaluates the leads found, and stores the result in the job."""
    global CACHED_LEADS

    def update(**kw):
        with _EMAIL_JOBS_LOCK:
            _EMAIL_JOBS[job_id].update(kw)

    try:
        invalid = [e for e in emails if not is_safe_email(e)]
        valid = [e for e in emails if is_safe_email(e)]
        frames = []
        for i in range(0, len(valid), EMAIL_LOOKUP_CHUNK):
            chunk = valid[i:i + EMAIL_LOOKUP_CHUNK]
            update(message=f"Looking up emails in Metabase: {min(i + len(chunk), len(valid)):,} of {len(valid):,}")
            part = fetch_leads_by_emails(chunk, chunk_size=EMAIL_LOOKUP_CHUNK)
            if len(part):
                frames.append(part)
            update(done=min(i + len(chunk), len(valid)))
        found = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if len(found) == 0:
            update(status="error", detail="None of the emails were found in Metabase, so there is nothing to recommend.")
            return
        # keep the order of the uploaded file
        order = {e: n for n, e in enumerate(valid)}
        found["_order"] = found["email"].astype(str).str.strip().str.lower().map(order)
        found = found.sort_values("_order").drop(columns=["_order"]).reset_index(drop=True)
        found_set = set(found["email"].astype(str).str.strip().str.lower())
        not_found = [e for e in valid if e not in found_set]

        update(message=f"Evaluating {len(found):,} leads")
        display, total = _evaluate_upload_in_chunks(found, f"CSV (Metabase lookup): {filename}")
        CACHED_LEADS = display

        warnings = []
        if stats.get("no_email"):
            warnings.append({"code": "rows_without_email", "count": stats["no_email"],
                             "message": f"{_count(stats['no_email'], 'row')} without an email {'was' if stats['no_email'] == 1 else 'were'} skipped."})
        if stats.get("duplicates"):
            warnings.append({"code": "duplicate_emails", "count": stats["duplicates"],
                             "message": f"{_count(stats['duplicates'], 'duplicate email')} {'was' if stats['duplicates'] == 1 else 'were'} merged."})
        if invalid:
            warnings.append({"code": "invalid_emails", "count": len(invalid),
                             "message": f"{_count(len(invalid), 'value')} in the email column {'is' if len(invalid) == 1 else 'are'} not a valid email address and {'was' if len(invalid) == 1 else 'were'} skipped."})
        if not_found:
            sample = ", ".join(not_found[:5]) + (" and more" if len(not_found) > 5 else "")
            warnings.append({"code": "emails_not_found", "count": len(not_found),
                             "message": f"{_count(len(not_found), 'email')} {'was' if len(not_found) == 1 else 'were'} not found in Metabase, so there is no recommendation for {'it' if len(not_found) == 1 else 'them'}: {sample}."})
        result = {
            "status": "success", "mode": "email_lookup", "filename": filename, "total": total, "displayed": len(display),
            "leads": display, "warnings": warnings, "limits": {"max_rows": MAX_UPLOAD_ROWS, "max_mb": MAX_UPLOAD_MB},
        }
        update(status="success", result=result, done=len(valid), message="Done")
    except Exception as e:
        import traceback
        traceback.print_exc()
        update(status="error", detail=f"Metabase lookup failed: {str(e)[:300]}")


def _start_email_lookup_job(emails: list, filename: str, stats: dict) -> dict:
    if not is_metabase_configured():
        raise HTTPException(status_code=400, detail="A file with only emails needs Metabase to look the leads up, but Metabase is not configured.")
    with _EMAIL_JOBS_LOCK:
        # forget finished jobs older than 30 minutes; allow one running lookup at a time
        for jid in [k for k, v in _EMAIL_JOBS.items() if _time.time() - v["started"] > 1800]:
            _EMAIL_JOBS.pop(jid, None)
        if any(v["status"] == "processing" for v in _EMAIL_JOBS.values()):
            raise HTTPException(status_code=409, detail="Another email lookup is still running. Please wait for it to finish.")
        job_id = uuid.uuid4().hex
        _EMAIL_JOBS[job_id] = {"status": "processing", "done": 0, "total": sum(1 for e in emails if is_safe_email(e)), "message": "Starting", "started": _time.time()}
    threading.Thread(target=_run_email_lookup_job, args=(job_id, emails, filename, stats), daemon=True).start()
    return {"status": "processing", "mode": "email_lookup", "job_id": job_id, "total": sum(1 for e in emails if is_safe_email(e))}


@app.get("/api/upload-job/{job_id}")
def upload_job_status(job_id: str):
    with _EMAIL_JOBS_LOCK:
        job = _EMAIL_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Unknown or expired lookup.")
        if job["status"] == "success":
            return _EMAIL_JOBS.pop(job_id)["result"]       # delivered once, then forgotten
        if job["status"] == "error":
            detail = job.get("detail", "Lookup failed.")
            _EMAIL_JOBS.pop(job_id, None)
            return {"status": "error", "detail": detail}
        return {"status": "processing", "done": job["done"], "total": job["total"], "message": job["message"]}


@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    Accepts user-uploaded CSV, evaluates all rows dynamically, stores in database, and returns evaluated leads.
    Includes multi-encoding fallback and memory protection.
    """
    global CACHED_LEADS, CACHED_DF
    try:
        contents = await file.read()
        if len(contents) > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File is {len(contents) / (1024 * 1024):.1f} MB, which exceeds the {MAX_UPLOAD_MB} MB limit.")
        df = None
        fname = (file.filename or '').lower()
        if fname.endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(io.BytesIO(contents))
            except Exception as e_xl:
                print(f"Excel read error: {e_xl}")

        if df is None:
            for enc in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding=enc, low_memory=False)
                    break
                except (UnicodeDecodeError, Exception):
                    continue

        if df is None:
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding='latin-1', sep=None, engine='python')
            except Exception:
                try:
                    df = pd.read_excel(io.BytesIO(contents))
                except Exception as final_e:
                    raise ValueError(f"Could not parse file as CSV or Excel: {final_e}")
        
        df = _validate_upload_structure(df)
        # Leads are identified by their real email only: drop rows without one, merge duplicates (keep the last row).
        email_col = find_col(df, _REQUIRED_UPLOAD_COLUMNS['email'])
        norm = df[email_col].astype(str).str.strip().str.lower()
        has_email = ~norm.isin(["", "nan", "none", "null"])
        stats = {"no_email": int((~has_email).sum())}
        df = df[has_email].copy()
        df[email_col] = norm[has_email]
        stats["duplicates"] = int(df.duplicated(subset=[email_col], keep="last").sum())
        df = df.drop_duplicates(subset=[email_col], keep="last").reset_index(drop=True)
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="No rows with an email were found. Leads are identified by their real email.")
        if find_col(df, _REQUIRED_UPLOAD_COLUMNS['role']) is None:
            # No role column: the file only identifies leads, so fetch each lead's details from Metabase and recommend for those.
            return _start_email_lookup_job(df[email_col].tolist(), file.filename or 'upload', stats)
        upload_warnings = _upload_warnings(df, stats)
        del contents
        source_label = f"CSV: {file.filename}"
        # Evaluate + store in chunks so peak memory stays small (a full 10,000-lead result set is ~400 MB in Python
        # objects, which would not fit a 512 MB instance). Runs in a worker thread so other users are not blocked.
        display_leads, total_count = await run_in_threadpool(_evaluate_upload_in_chunks, df, source_label)
        del df
        import gc
        gc.collect()

        # Only the first UPLOAD_DISPLAY_LEADS are kept in memory / returned; the page streams the rest from SQLite.
        CACHED_LEADS = display_leads
        initial_leads = display_leads

        return {
            "status": "success",
            "filename": file.filename,
            "total": total_count,
            "displayed": len(initial_leads),
            "leads": initial_leads,
            "warnings": upload_warnings,
            "limits": {"max_rows": MAX_UPLOAD_ROWS, "max_mb": MAX_UPLOAD_MB},
            "curriculum_catalog": get_all_curricula_catalog()
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Failed to process CSV: {str(e)}")


@app.get("/api/leads/more")
async def get_more_leads(offset: int = 0, limit: int = 1000):
    """
    Progressive chunked loader: Fetches the next batch of evaluated leads.
    Serves from memory cache if populated, else falls back to SQLite.
    """
    global CACHED_LEADS
    limit = max(1, min(limit, 1000))   # small pages keep memory flat on a 512 MB instance
    if CACHED_LEADS and len(CACHED_LEADS) > offset:
        leads_slice = CACHED_LEADS[offset:offset + limit]
        return {
            "status": "success",
            "offset": offset,
            "limit": limit,
            "total": len(CACHED_LEADS),
            "returned": len(leads_slice),
            "leads": leads_slice
        }

    total = get_total_leads_count()
    leads = get_recent_leads(limit=limit, offset=offset)
    return {
        "status": "success",
        "offset": offset,
        "limit": limit,
        "total": total,
        "returned": len(leads),
        "leads": leads
    }


@app.post("/api/crm/webhook")
async def crm_webhook(lead: CRMWebhookLead):
    """
    Dynamic Inbound CRM Webhook: Receives a new lead from Salesforce / HubSpot / LeadSquared in real time,
    evaluates program recommendation + track + duration + academic eligibility, captures touchpoints,
    saves to SQLite, and returns full dossier.
    """
    global CACHED_LEADS
    import time
    lead_dict = {
        'name': lead.name or "",
        'email': lead.email,
        'phone': lead.phone or "",
        'role': lead.role or "",
        'experience': lead.experience or "",
        'education': lead.education or "Graduated / Degree",
        'company type': lead.company_type or "",
        'previous org name': lead.previous_org or "",
        'program': lead.program or "Academy",
        'set_score': lead.set_score or lead.sat_score or "N/A",
        'set_status': (lead.set_status or lead.sat_status or "SET Not Attempted").replace('SAT', 'SET').replace('sat', 'set'),
        'sat_score': lead.set_score or lead.sat_score or "N/A",
        'sat_status': (lead.set_status or lead.sat_status or "SET Not Attempted").replace('SAT', 'SET').replace('sat', 'set')
    }
    
    real_id = (lead.lead_id or "").strip() or (lead.email or "").strip().lower()
    if not real_id:
        raise HTTPException(status_code=400, detail="A lead id or an email is required; identifiers are never generated.")
    eval_res = evaluate_lead_profile(lead_dict)
    eval_res['lead_id'] = (lead.lead_id or "").strip()
    eval_res['_uid'] = real_id
    
    touchpoint_dict = {
        'summary': f"{lead.attended} - {lead.event_name[:40]}",
        'event_name': lead.event_name,
        'attended': lead.attended,
        'duration': lead.duration,
        'sat_status': lead_dict['sat_status'],
        'sat_score': lead_dict['sat_score'],
        'set_status': lead_dict['set_status'],
        'set_score': lead_dict['set_score'],
        'channel': lead.channel,
        'campaign': "Live CRM Inbound",
        'platform': "Web / CRM API",
        'geography': "Not available",
        'signup_date': datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        'lead_score': "Not available",
        'landing_page': "Not available"
    }
    eval_res['touchpoints'] = touchpoint_dict
    
    # Save to SQLite database for instant search
    save_evaluated_lead(eval_res, source="CRM_WEBHOOK")
    
    # Prepend to memory cache so UI live updates
    CACHED_LEADS.insert(0, eval_res)
    
    return {
        "status": "success",
        "message": "Lead ingested, evaluated, and indexed successfully",
        "lead": eval_res
    }

@app.post("/api/evaluate-single")
async def evaluate_single(lead_input: SingleLeadInput):
    """
    Evaluates a single lead entered directly by the sales counselor on the UI.
    """
    global CACHED_LEADS, CACHED_DF
    single_set_status = (lead_input.set_status or lead_input.sat_status or "SET Not Attempted").replace('SAT', 'SET').replace('sat', 'set')
    single_set_score = lead_input.set_score or lead_input.sat_score or "N/A"
    lead_dict = {
        'name': lead_input.name or "",
        'email': (lead_input.email or "").strip(),
        'phone': lead_input.phone or "",
        'role': lead_input.role,
        'experience': lead_input.experience,
        'education': lead_input.education or "Graduated / Degree",
        'company type': lead_input.company_type or "",
        'previous org name': lead_input.previous_org or "",
        'previous org year': lead_input.previous_org_year or "",
        'program': lead_input.program or "Academy",
        'set_score': single_set_score,
        'set_status': single_set_status,
        'sat_score': single_set_score,
        'sat_status': single_set_status
    }
    
    eval_res = evaluate_lead_profile(lead_dict)
    manual_email = (lead_input.email or "").strip().lower()
    eval_res['lead_id'] = ""
    eval_res['_uid'] = manual_email   # empty when no email was typed: the result is shown but not stored
    
    touchpoint_dict = {
        'summary': "Manual Counselor Ingestion",
        'event_name': "Direct Counselor Intake",
        'attended': "Phone Inbound",
        'duration': "N/A",
        'sat_status': single_set_status,
        'sat_score': single_set_score,
        'set_status': single_set_status,
        'set_score': single_set_score,
        'channel': "Sales Inbound Desk",
        'campaign': "Direct Counselor Inquiry",
        'platform': "Counselor Console",
        'geography': "Not available",
        'signup_date': datetime.datetime.utcnow().strftime("%Y-%m-%d"),
        'lead_score': "Not available",
        'landing_page': "Not available"
    }
    eval_res['touchpoints'] = touchpoint_dict

    if manual_email:   # without a real identifier nothing is saved or cached
        save_evaluated_lead(eval_res, source="MANUAL_INTAKE")
        CACHED_LEADS.insert(0, eval_res)
    
    return {
        "status": "success",
        "lead": eval_res
    }

@app.get("/api/lookup")
async def lookup_lead(q: str, scope: Optional[str] = None):
    """
    Looks up a lead by email, phone, name, or lead ID.
    When scope='mis', it strictly queries Marketing MIS / Metabase / live CRM lookups
    and isolates from bulk CSV upload data.
    """
    global CACHED_LEADS
    q_clean = q.strip().lower()
    is_mis_only = (scope == "mis")
    
    # 1. Pure On-Demand: When searching by email for Marketing MIS, query Metabase live directly
    if is_mis_only:
        try:
            mb_row = await run_in_threadpool(fetch_lead_by_email_from_metabase, q_clean)
            if mb_row:
                mb_email = str(mb_row.get('email') or mb_row.get('Email') or q_clean).strip().lower()
                mb_org = mb_row.get('orgname') or mb_row.get('previous org name') or ''
                mb_role = mb_row.get('role') or mb_row.get('Role') or ''
                raw_mb_exp = mb_row.get('experience') if mb_row.get('experience') is not None else mb_row.get('Experience')
                if raw_mb_exp is not None and str(raw_mb_exp).strip() not in ['', 'None', 'nan', 'null']:
                    mb_exp_clean = str(raw_mb_exp).strip()
                    try:
                        exp_num = float(mb_exp_clean)
                        # In Metabase temp.marketing_mis, the experience column is stored as total MONTHS
                        # (Common multiples: 6, 12, 18, 24, 30, 36, 48, 60, 72, 84, 96, 108, 120, etc.)
                        # Values >= 6 are treated as months unless they are an unrealistic number (> 480 mos = 40 yrs)
                        if 6.0 <= exp_num <= 480.0:
                            years_val = round(exp_num / 12.0, 1)
                            mb_exp = f"{int(years_val) if years_val.is_integer() else years_val} yrs ({int(exp_num)} mos)"
                        elif exp_num > 480.0:
                            # Garbled number in MIS (e.g. phone number or timestamp passed into exp)
                            mb_exp = "Not Specified"
                        elif 0.0 < exp_num < 6.0:
                            # 1 to 5: could be months or years; express clearly
                            mb_exp = f"{int(exp_num) if exp_num.is_integer() else exp_num} yrs"
                        else:
                            mb_exp = "0 years"
                    except ValueError:
                        mb_exp = mb_exp_clean
                else:
                    mb_exp = ''
                mb_comp = mb_row.get('company_type') or mb_row.get('Company Type') or ''

                normalized_lead = {
                    'name': mb_row.get('name') or mb_row.get('Name') or '',
                    'email': mb_email,
                    'phone': str(mb_row.get('phone') or mb_row.get('Phone') or 'N/A'),
                    'role': mb_role,
                    'experience': mb_exp,
                    'education': mb_row.get('education') or mb_row.get('Education') or 'Graduated / Degree',
                    'education_missing': not (mb_row.get('education') or mb_row.get('Education')),
                    'company type': mb_comp,
                    'previous org name': mb_org,
                    'previous org year': str(mb_row.get('orgyear') or mb_row.get('previous org year') or ''),
                    'program': mb_row.get('program_type') or mb_row.get('program') or mb_row.get('which_bda_team') or 'Academy',
                    'set_status': 'SET Passed' if str(mb_row.get('test_passed_flag')) == '1' else ('SET Attempted' if str(mb_row.get('test_launched_flag')) == '1' else 'SET Not Attempted'),
                    'set_score': 'Passed (Cleared)' if str(mb_row.get('test_passed_flag')) == '1' else 'Attempted',
                    'crm': {k: mb_row.get(k) for k in ('program_type', 'which_bda_team', 'event_name', 'event_type', 'landing_page_url', 'utm_source', 'country_type',
                                                       'orgname', 'orgyear', 'test_passed_flag', 'company_type', 'role', 'attended', 'minutes_in_event', 'event_rank_registraion')},
                }
                eval_res = evaluate_lead_profile(normalized_lead)
                raw_mb_id = str(mb_row.get('lead_id') or mb_row.get('Lead ID') or '').strip()
                lead_id = "" if raw_mb_id.lower() in ['nan', 'none', 'null', 'n/a', ''] else raw_mb_id
                eval_res['lead_id'] = lead_id
                eval_res['_uid'] = lead_id or mb_email   # real Metabase lead id if present, else the lead's email
                eval_res['source'] = "METABASE_LIVE"
                # Metabase holds no education value, so graduation is an assumption. Say so wherever the lead is shown.
                _basis = eval_res.get('person', {}).get('education_basis')
                eval_res['data_quality_flags'] = [] if mb_row.get('education') else (['education_inferred_from_experience'] if _basis == 'inferred' else ['education_assumed_graduate'])
                eval_res['touchpoints'] = {
                    'summary': f"Marketing MIS - {mb_row.get('event_name') or mb_row.get('event_type') or mb_row.get('program_type') or 'Live MIS Inquiry'}",
                    'event_name': mb_row.get('event_name') or mb_row.get('event_type') or 'Direct MIS Query',
                    'attended': 'Attended' if str(mb_row.get('attended_before_payment_flag')) == '1' else 'Registered',
                    'duration': str(mb_row.get('duration') or 'N/A'),
                    'sat_status': normalized_lead['set_status'],
                    'sat_score': normalized_lead['set_score'],
                    'set_status': normalized_lead['set_status'],
                    'set_score': normalized_lead['set_score'],
                    'channel': " / ".join(x for x in [str(mb_row.get('utm_source') or '').strip(), str(mb_row.get('utm_medium') or '').strip()] if x) or 'Not available',
                    'campaign': str(mb_row.get('utm_campaign') or mb_row.get('batch') or 'Not available'),
                    'platform': str(mb_row.get('platform') or 'Not available'),
                    'geography': str(mb_row.get('country_type') or 'Not available'),
                    'signup_date': str(mb_row.get('signed_up_date') or mb_row.get('lead_created_at') or 'Not available'),
                    'lead_score': str(mb_row.get('lead_score') or 'Not available'),
                    'landing_page': str(mb_row.get('landing_page_url') or 'Not available')
                }
                # A single-lead lookup is shown to the counselor and nothing more: it is not added to the results list
                # (which is for uploaded files) and it is not stored, so no lead data is kept beyond the request.
                return {"status": "success", "source": "metabase_live", "lead": eval_res}
        except MetabaseUnavailable as e:
            print(f"[MIS Lookup] Metabase unavailable: {e}")
            return {"status": "unavailable", "message": "Metabase did not respond, so we cannot tell whether this lead exists. Please try again."}
        except Exception as e:
            print(f"[MIS Lookup Error] {e}")
            import traceback
            traceback.print_exc()
        return {"status": "not_found", "message": f"No record found in Marketing MIS matching '{q}'."}

    # 2. General CRM / Search lookup (checks RAM & local database)
    for lead in CACHED_LEADS:
        p = lead.get('person', {})
        if (p.get('email', '').strip().lower() == q_clean or
            p.get('name', '').strip().lower() == q_clean or
            lead.get('lead_id', '').strip().lower() == q_clean or
            q_clean in p.get('email', '').lower() or
            q_clean in str(p.get('phone', ''))):
            return {"status": "success", "source": lead.get('source', 'memory_cache'), "lead": lead}

    db_lead = find_lead_by_query(q_clean)
    if db_lead:
        return {"status": "success", "source": "crm_database", "lead": db_lead}

    # 3. Fallback: If not found in cache/db and query looks like an email or phone, check live Marketing MIS
    if "@" in q_clean or (q_clean.replace("+", "").replace("-", "").isdigit() and len(q_clean) >= 10):
        try:
            return await lookup_lead(q=q, scope="mis")
        except Exception:
            pass

    return {"status": "not_found", "message": f"No lead found in CRM matching '{q}'."}

class AppendLeadInput(BaseModel):
    name: str = "Prospective Learner"
    email: str
    phone: Optional[str] = "N/A"
    role: str = "Software Professional"
    experience: str = "Not Specified"
    education: Optional[str] = "Graduated / Degree"
    company_type: Optional[str] = "IT Services / Technology"
    previous_org: Optional[str] = "Current Company"
    program: Optional[str] = "Academy"
    set_status: Optional[str] = "Passed"
    set_score: Optional[str] = "80"

@app.get("/api/csv-stream/status")
async def get_csv_stream_status():
    """Returns status and file details for the incoming watched CSV file."""
    return {
        "status": "success",
        "details": get_watched_csv_status()
    }

@app.post("/api/csv-stream/sync")
async def trigger_csv_stream_sync():
    """Forces an immediate sync of the incoming watched CSV file."""
    global CACHED_LEADS
    res = sync_watched_csv(force=True, memory_cache_ref=CACHED_LEADS)
    return res

@app.get("/api/csv-stream/leads")
async def get_csv_stream_leads():
    """
    Returns initial batch of evaluated leads with total count so dashboard retains
    complete state across browser refresh without proxy timeout / 502 payload size issues.
    """
    global CACHED_LEADS
    # 1. If memory cache has evaluated leads, return initial batch with full total
    if CACHED_LEADS and len(CACHED_LEADS) > 0:
        return {
            "status": "success",
            "total": len(CACHED_LEADS),
            "leads": CACHED_LEADS[:5000]
        }

    # 2. Query database for initial batch and true total
    total = get_total_leads_count()
    leads = get_recent_leads(limit=5000, offset=0)
    if leads:
        CACHED_LEADS = leads
        
    return {
        "status": "success",
        "total": total,
        "leads": leads
    }

@app.post("/api/csv-stream/append")
async def append_lead_to_csv_endpoint(lead_input: AppendLeadInput):
    """
    Appends a new lead to the incoming watched CSV file and triggers auto-evaluation.
    """
    res = append_lead_to_csv(lead_input.dict())
    return res

@app.post("/api/metabase/sync")
async def sync_metabase(force: bool = False):
    """
    Dynamically pulls latest query results from Metabase API, evaluates all records,
    persists them in SQLite database, updates memory cache, and updates master CSV.
    """
    global CACHED_LEADS, CACHED_DF
    if not is_metabase_configured():
        return {
            "status": "not_configured",
            "message": "Metabase connection is not configured yet. Open metabase_config.json to add your Metabase URL and Card ID or Public UUID."
        }
        
    try:
        df = await run_in_threadpool(fetch_leads_from_metabase, force)
        if df.empty:
            return {"status": "empty", "message": "Metabase query returned 0 rows."}
            
        evaluated_all, _ = await run_in_threadpool(process_leads_dataframe, df, False)
        await run_in_threadpool(bulk_save_evaluated_leads, evaluated_all, "METABASE_SYNC")
        CACHED_LEADS = evaluated_all
        
        return {
            "status": "success",
            "total_synced": len(evaluated_all),
            "message": f"Successfully pulled and evaluated {len(evaluated_all)} leads from Metabase.",
            "leads": CACHED_LEADS
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Metabase sync failed: {str(e)}")

@app.get("/api/metabase/status")
async def metabase_status():
    cfg = load_metabase_config()
    configured = is_metabase_configured()
    return {
        "configured": configured,
        "metabase_url": cfg.get("metabase_url", ""),
        "card_id": cfg.get("card_id", ""),
        "has_public_uuid": bool(cfg.get("public_uuid")),
        "has_api_key": bool(cfg.get("api_key"))
    }

from fastapi.responses import Response, StreamingResponse
import csv as csv_module

CSV_EXPORT_HEADERS = [
    'Lead ID', 'Candidate Name', 'Email', 'Phone', 'Current Role',
    'Total Experience', 'Education', 'Company Type', 'Previous Organization',
    'Enquired Program', 'Primary Program', 'Primary Track', 'Primary Fit Tier',
    'Primary Duration', 'Retention Rate (%)', 'Refund Risk (%)', 'Primary Rationale',
    'Fallback Program', 'Fallback Track', 'Fallback Rationale',
    'Also Consider Program', 'Also Consider Chance (%)', 'Also Consider Program Refund (%)',
    'Call Opening Pitch', 'Program Pitch', 'Inbound Handling',
    'Diagnostic SET Status', 'Diagnostic SET Score', 'Ingestion Source', 'Evaluated At'
]

def _lead_to_row(data: dict, src: str = '', dt: str = '') -> dict:
    """Converts an evaluated lead dict to a flat export row."""
    p = data.get('person', {})
    prim = data.get('primary', {}) or {}
    fall = data.get('fallback', {}) or {}
    tp = data.get('touchpoints', {}) or {}
    ss = data.get('sales_script', {}) or {}
    return {
        'Lead ID': data.get('lead_id', ''),
        'Candidate Name': p.get('name', ''),
        'Email': p.get('email', ''),
        'Phone': p.get('phone', ''),
        'Current Role': p.get('role', ''),
        'Total Experience': p.get('experience', ''),
        'Education': p.get('education', ''),
        'Company Type': p.get('company_type', ''),
        'Previous Organization': p.get('previous_org', ''),
        'Enquired Program': p.get('enquired_program', p.get('program', 'N/A')),
        'Primary Program': prim.get('program', ''),
        'Primary Track': prim.get('track', ''),
        'Primary Fit Tier': prim.get('fit_tier', ''),
        'Primary Duration': prim.get('duration', ''),
        'Retention Rate (%)': prim.get('retention_rate', ''),
        'Refund Risk (%)': prim.get('refund_rate', ''),
        'Primary Rationale': prim.get('why', ''),
        'Fallback Program': fall.get('program', ''),
        'Fallback Track': fall.get('track', ''),
        'Fallback Rationale': fall.get('why', ''),
        'Also Consider Program': (data.get('also_consider') or {}).get('program', ''),
        'Also Consider Chance (%)': (data.get('also_consider') or {}).get('chance_pct', ''),
        'Also Consider Program Refund (%)': (data.get('also_consider') or {}).get('program_refund_rate', ''),
        'Call Opening Pitch': ss.get('call_opening', ''),
        'Program Pitch': ss.get('program_pitch', ''),
        'Inbound Handling': ss.get('inbound_handling', ''),
        'Diagnostic SET Status': tp.get('set_status', tp.get('sat_status', 'SET Not Attempted')),
        'Diagnostic SET Score': tp.get('set_score', tp.get('sat_score', 'N/A')),
        'Ingestion Source': src or data.get('source', ''),
        'Evaluated At': dt
    }

@app.get("/api/export")
async def export_crm_data(format: str = "csv"):
    """
    Exports evaluated leads as a streaming CSV or Excel file.
    Reads from in-memory cache first (immediate after upload),
    then falls back to chunked SQLite reads to prevent OOM and proxy timeouts.
    """
    global CACHED_LEADS
    format_clean = format.lower().strip()

    # --- EXCEL: load from memory or SQLite (small-medium datasets) ---
    if format_clean in ('xlsx', 'excel'):
        records = []
        if CACHED_LEADS:
            for data in CACHED_LEADS:
                try:
                    records.append(_lead_to_row(data))
                except Exception:
                    continue
        else:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT evaluated_json, source, created_at FROM leads ORDER BY created_at DESC;")
                for row in cursor.fetchall():
                    try:
                        records.append(_lead_to_row(json.loads(row['evaluated_json']), row['source'], row['created_at']))
                    except Exception:
                        continue
            finally:
                conn.close()
        if not records:
            raise HTTPException(status_code=404, detail="No evaluated leads found. Please upload a CSV first.")
        df_export = pd.DataFrame(records, columns=CSV_EXPORT_HEADERS)
        return create_export_response(df_export, 'xlsx')

    # --- CSV: true streaming generator - never loads all rows into RAM ---
    def csv_row_generator():
        """Yields UTF-8 BOM + header + rows from memory cache or SQLite in chunks."""
        buf = io.StringIO()
        writer = csv_module.DictWriter(buf, fieldnames=CSV_EXPORT_HEADERS, extrasaction='ignore', lineterminator='\n')
        # UTF-8 BOM so Excel opens correctly
        yield '\ufeff'
        writer.writeheader()
        yield buf.getvalue()

        if CACHED_LEADS:
            for data in CACHED_LEADS:
                try:
                    row_dict = _lead_to_row(data)
                    buf = io.StringIO()
                    writer = csv_module.DictWriter(buf, fieldnames=CSV_EXPORT_HEADERS, extrasaction='ignore', lineterminator='\n')
                    writer.writerow(row_dict)
                    yield buf.getvalue()
                except Exception:
                    continue
        else:
            # Chunked SQLite read - 500 rows at a time
            conn = get_connection()
            try:
                cursor = conn.cursor()
                offset = 0
                chunk_size = 500
                while True:
                    cursor.execute(
                        "SELECT evaluated_json, source, created_at FROM leads ORDER BY created_at DESC LIMIT ? OFFSET ?;",
                        (chunk_size, offset)
                    )
                    chunk = cursor.fetchall()
                    if not chunk:
                        break
                    for db_row in chunk:
                        try:
                            row_dict = _lead_to_row(json.loads(db_row['evaluated_json']), db_row['source'], db_row['created_at'])
                            buf = io.StringIO()
                            writer = csv_module.DictWriter(buf, fieldnames=CSV_EXPORT_HEADERS, extrasaction='ignore', lineterminator='\n')
                            writer.writerow(row_dict)
                            yield buf.getvalue()
                        except Exception:
                            continue
                    offset += chunk_size
            finally:
                conn.close()

    from datetime import date
    filename = f"scaler_evaluated_leads_{date.today().isoformat()}.csv"
    return StreamingResponse(
        csv_row_generator(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition",
            "X-Content-Type-Options": "nosniff"
        }
    )


def create_export_response(df_export: pd.DataFrame, format_clean: str):
    if format_clean in ['xlsx', 'excel']:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Evaluated Leads')
        output.seek(0)
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=scaler_evaluated_leads.xlsx",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    else:
        csv_buffer = io.StringIO()
        df_export.to_csv(csv_buffer, index=False, encoding='utf-8')
        return Response(
            content=csv_buffer.getvalue().encode('utf-8-sig'),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=scaler_evaluated_leads.csv",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )


@app.post("/api/export/active")
async def export_active_leads(payload: dict = Body(...), format: str = "csv"):
    """
    Exports leads sent directly from the client's current session/filters.
    Works seamlessly with Option 2 (zero server disk storage for on-demand leads).
    """
    leads = payload.get("leads", [])
    if not leads:
        raise HTTPException(status_code=400, detail="No leads provided in export payload.")

    records = []
    for data in leads:
        try:
            p = data.get('person', {})
            prim = data.get('primary', {})
            fall = data.get('fallback', {})
            tp = data.get('touchpoints', {})
            records.append({
                'Lead ID': data.get('lead_id', ''),
                'Candidate Name': p.get('name', ''),
                'Email': p.get('email', ''),
                'Phone': p.get('phone', ''),
                'Current Role': p.get('role', ''),
                'Total Experience': p.get('experience', ''),
                'Education': p.get('education', ''),
                'Company Type': p.get('company_type', ''),
                'Previous Organization': p.get('previous_org', ''),
                'Enquired Program': p.get('enquired_program', p.get('program', 'N/A')),
                'Primary Program': prim.get('program', ''),
                'Primary Track': prim.get('track', ''),
                'Primary Fit Tier': prim.get('fit_tier', ''),
                'Primary Duration': prim.get('duration', ''),
                'Retention Rate (%)': prim.get('retention_rate', ''),
                'Refund Risk (%)': prim.get('refund_rate', ''),
                'Primary Logic': prim.get('fit_rationale', ''),
                'Fallback Program': fall.get('program', ''),
                'Fallback Track': fall.get('track', ''),
                'Fallback Logic': fall.get('fit_rationale', ''),
                'Also Consider Program': (data.get('also_consider') or {}).get('program', ''),
                'Also Consider Chance (%)': (data.get('also_consider') or {}).get('chance_pct', ''),
                'Diagnostic SET Status': tp.get('set_status', tp.get('sat_status', 'SET Not Attempted')),
                'Diagnostic SET Score': tp.get('set_score', tp.get('sat_score', 'N/A')),
                'Ingestion Source': data.get('source', 'MIS On-Demand'),
                'Evaluated At': data.get('evaluated_at', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            })
        except Exception:
            continue

    df_export = pd.DataFrame(records)
    return create_export_response(df_export, format.lower().strip())

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("Program_Evaluator_Sales.src.server:app", host="127.0.0.1", port=8000, reload=True)

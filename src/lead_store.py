import os
import sqlite3
import json
import re
from typing import Optional, Dict, Any, List

DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output'))
DB_PATH = os.getenv("DATABASE_PATH", os.path.join(DATA_DIR, 'leads_store.db'))

def get_connection():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            lead_id TEXT PRIMARY KEY,
            email TEXT,
            email_lower TEXT,
            phone TEXT,
            name TEXT,
            role TEXT,
            experience TEXT,
            education TEXT,
            education_level TEXT,
            company_type TEXT,
            previous_org TEXT,
            source TEXT DEFAULT 'CSV_UPLOAD',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            evaluated_json TEXT
        );
    """)
    # Check if education columns need to be added to an existing table
    try:
        cursor.execute("ALTER TABLE leads ADD COLUMN education TEXT;")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE leads ADD COLUMN education_level TEXT;")
    except Exception:
        pass
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_email_lower ON leads(email_lower);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);")
    conn.commit()
    conn.close()

def save_evaluated_lead(eval_res: Dict[str, Any], source: str = "CRM_WEBHOOK") -> bool:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    p = eval_res.get('person', {})
    email = p.get('email', '') or ''
    email_lower = email.strip().lower()
    # Identity is the real lead id or the real email; never a generated value.
    lead_id = eval_res.get('lead_id') or eval_res.get('_uid') or email_lower
    if not lead_id:
        conn.close()
        return False
    phone = re.sub(r'\D', '', str(p.get('phone', '')))
    education = p.get('education', '')
    education_level = p.get('education_level', 'GRAD_UNKNOWN')
    
    cursor.execute("""
        INSERT INTO leads (lead_id, email, email_lower, phone, name, role, experience, education, education_level, company_type, previous_org, source, evaluated_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(lead_id) DO UPDATE SET
            email = excluded.email,
            email_lower = excluded.email_lower,
            phone = excluded.phone,
            name = excluded.name,
            role = excluded.role,
            experience = excluded.experience,
            education = excluded.education,
            education_level = excluded.education_level,
            company_type = excluded.company_type,
            previous_org = excluded.previous_org,
            source = excluded.source,
            evaluated_json = excluded.evaluated_json;
    """, (
        lead_id,
        email,
        email_lower,
        phone,
        p.get('name', 'Prospective Learner'),
        p.get('role', ''),
        p.get('experience', ''),
        education,
        education_level,
        p.get('company_type', ''),
        p.get('previous_org', ''),
        source,
        json.dumps({
            'lead_id': lead_id,
            'person': p,
            'primary': {k: v for k, v in eval_res.get('primary', {}).items() if k not in ['curriculum_modules', 'market_intelligence']},
            'fallback': {k: v for k, v in eval_res.get('fallback', {}).items() if k not in ['curriculum_modules', 'market_intelligence']},
            'sales_script': eval_res.get('sales_script', {}),
            'touchpoints': eval_res.get('touchpoints', {})
        })
    ))
    conn.commit()
    conn.close()
    return True

def bulk_save_evaluated_leads(records: List[Dict[str, Any]], source: str = "CSV_UPLOAD", replace_existing: bool = False) -> int:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    if replace_existing:
        # Clear previously uploaded bulk CSV records so the new batch does not accumulate old leads
        cursor.execute("DELETE FROM leads WHERE source LIKE 'CSV:%' OR source = 'CSV_UPLOAD';")
        conn.commit()
    
    batch = []
    for idx, r in enumerate(records):
        p = r.get('person', {})
        lead_id = r.get('lead_id', '')
        email = p.get('email', '') or ''
        email_lower = email.strip().lower()
        db_key = r.get('_uid') or lead_id or email_lower
        if not db_key:
            continue   # no real identifier: do not store
        phone = re.sub(r'\D', '', str(p.get('phone', '')))
        education = p.get('education', '')
        education_level = p.get('education_level', 'GRAD_UNKNOWN')
        # Compact JSON to prevent massive database bloat
        r_clean = {
            'lead_id': lead_id,
            '_uid': db_key,
            'person': p,
            'primary': {k: v for k, v in r.get('primary', {}).items() if k not in ['curriculum_modules', 'market_intelligence']},
            'fallback': {k: v for k, v in r.get('fallback', {}).items() if k not in ['curriculum_modules', 'market_intelligence']},
            'sales_script': r.get('sales_script', {}),
            'touchpoints': r.get('touchpoints', {})
        }
        batch.append((
            db_key,
            email,
            email_lower,
            phone,
            p.get('name', ''),
            p.get('role', ''),
            p.get('experience', ''),
            education,
            education_level,
            p.get('company_type', ''),
            p.get('previous_org', ''),
            source,
            json.dumps(r_clean)
        ))
        
    cursor.executemany("""
        INSERT INTO leads (lead_id, email, email_lower, phone, name, role, experience, education, education_level, company_type, previous_org, source, evaluated_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(lead_id) DO UPDATE SET
            email = excluded.email,
            email_lower = excluded.email_lower,
            phone = excluded.phone,
            name = excluded.name,
            role = excluded.role,
            experience = excluded.experience,
            education = excluded.education,
            education_level = excluded.education_level,
            company_type = excluded.company_type,
            previous_org = excluded.previous_org,
            source = excluded.source,
            evaluated_json = excluded.evaluated_json;
    """, batch)
    conn.commit()
    count = cursor.rowcount
    conn.close()
    return count

def find_lead_by_query(query: str, exclude_bulk_csv: bool = False) -> Optional[Dict[str, Any]]:
    init_db()
    q = query.strip()
    if not q:
        return None
        
    conn = get_connection()
    cursor = conn.cursor()
    q_lower = q.lower()
    
    where_source = "AND source NOT LIKE 'CSV:%' AND source != 'CSV_UPLOAD'" if exclude_bulk_csv else ""
    order_clause = "ORDER BY CASE WHEN source = 'METABASE_LIVE_LOOKUP' THEN 0 WHEN source = 'CRM_WEBHOOK' THEN 1 ELSE 2 END, created_at DESC LIMIT 1;"
    
    # Helper to return formatted lead with lead_id and source
    def format_row(r):
        data = json.loads(r['evaluated_json'])
        data['lead_id'] = data.get('lead_id', '')
        data['_uid'] = data.get('_uid') or r['lead_id']
        data['source'] = r['source']
        return data

    # 1. Exact email match (case-insensitive)
    cursor.execute(f"SELECT lead_id, source, evaluated_json FROM leads WHERE email_lower = ? {where_source} {order_clause}", (q_lower,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return format_row(row)
        
    # 2. Exact lead_id match
    cursor.execute(f"SELECT lead_id, source, evaluated_json FROM leads WHERE UPPER(lead_id) = ? {where_source} {order_clause}", (q.upper(),))
    row = cursor.fetchone()
    if row:
        conn.close()
        return format_row(row)

    # 3. Exact full name match (case-insensitive)
    cursor.execute(f"SELECT lead_id, source, evaluated_json FROM leads WHERE LOWER(name) = ? {where_source} {order_clause}", (q_lower,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return format_row(row)

    # 4. Name prefix match (e.g. "Faizan" -> "Faizan Ahmed")
    cursor.execute(f"SELECT lead_id, source, evaluated_json FROM leads WHERE LOWER(name) LIKE ? {where_source} {order_clause}", (f"{q_lower}%",))
    row = cursor.fetchone()
    if row:
        conn.close()
        return format_row(row)

    # 5. Name contains query
    cursor.execute(f"SELECT lead_id, source, evaluated_json FROM leads WHERE LOWER(name) LIKE ? {where_source} {order_clause}", (f"%{q_lower}%",))
    row = cursor.fetchone()
    if row:
        conn.close()
        return format_row(row)

    # 6. Phone match (normalized digits)
    digits = re.sub(r'\D', '', q)
    if len(digits) >= 7:
        cursor.execute(f"SELECT lead_id, source, evaluated_json FROM leads WHERE phone LIKE ? {where_source} {order_clause}", (f"%{digits}%",))
        row = cursor.fetchone()
        if row:
            conn.close()
            return format_row(row)
            
    # 7. Partial email or lead_id match as last resort
    cursor.execute(f"""
        SELECT lead_id, source, evaluated_json FROM leads 
        WHERE (email_lower LIKE ? OR lead_id LIKE ?) {where_source}
        {order_clause}
    """, (f"%{q_lower}%", f"%{q.upper()}%"))
    row = cursor.fetchone()
    conn.close()
    if row:
        return format_row(row)
        
    return None

def get_recent_leads(limit: int = 5000, offset: int = 0) -> List[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT evaluated_json, source, lead_id FROM leads ORDER BY rowid ASC LIMIT ? OFFSET ?;", (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        try:
            d = json.loads(r['evaluated_json'])
            d['lead_id'] = d.get('lead_id', '')
            d['_uid'] = d.get('_uid') or r['lead_id']
            d['source'] = r['source']
            results.append(d)
        except Exception:
            continue
    return results

def get_total_leads_count() -> int:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM leads;")
    row = cursor.fetchone()
    conn.close()
    return row['cnt'] if row else 0

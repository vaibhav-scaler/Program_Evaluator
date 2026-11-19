"""
The lead as a counselor sees them when the lead ARRIVES.

A lead often has many records in Metabase (a median of 6): one for each program or event they enquired about, plus one created around the
sale itself. The record that is "most complete" today is usually that last one, and it carries things a new lead does not have yet (for
example the team that closed the sale). Training and judging the tool on it makes the tool look better than it is.

So for training, calibration and the monthly review, each learner is represented by the records that existed in the first days of
their life (default: 1 day after the first record), taking the most complete of those. Measured on months the model had not seen,
this view gives the honest accuracy; the older way was about 3 points too high.

The live lookup is unchanged: it reads whatever the lead has in Metabase right now.
"""
from typing import List

import pandas as pd

from .metabase_client import LOOKUP_COLUMNS, export_native_query, is_safe_email

ARRIVAL_WINDOW_DAYS = 1
_FIELDS = LOOKUP_COLUMNS + ", registration_date1"


def fetch_records(emails: List[str], chunk_size: int = 400) -> pd.DataFrame:
    """Every record for these emails (no one-per-email filter), downloaded in small chunks with retries."""
    safe = [e for e in dict.fromkeys(emails) if is_safe_email(e)]
    frames = []
    for i in range(0, len(safe), chunk_size):
        chunk = safe[i:i + chunk_size]
        in_list = ",".join("'" + e + "'" for e in chunk)
        rows = None
        for _attempt in (1, 2, 3):
            try:
                rows = export_native_query(f"select {_FIELDS} from temp.marketing_mis where lower(email) in ({in_list})")
                break
            except Exception:
                rows = None
        if rows is None:
            raise RuntimeError("Metabase did not answer after three tries; nothing was changed. Run it again later.")
        if rows:
            frames.append(pd.DataFrame(rows))
        print(f"  Metabase records {min(i + chunk_size, len(safe))}/{len(safe)}", flush=True)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if len(out):
        out["email"] = out["email"].astype(str).str.lower()
    return out


def _completeness(df: pd.DataFrame) -> pd.Series:
    def filled(c):
        s = df[c].astype(str).str.strip().str.lower()
        return (df[c].notna() & ~s.isin(["", "none", "nan"])).astype(int)
    return (filled("role") + (pd.to_numeric(df["experience"], errors="coerce").fillna(0) > 0).astype(int) + filled("orgname")
            + df["orgyear"].notna().astype(int) + filled("company_type") + filled("program_type"))


def arrival_record(records: pd.DataFrame, window_days: int = ARRIVAL_WINDOW_DAYS) -> pd.DataFrame:
    """One record per email: among the records registered within `window_days` of the email's first one, the most complete (then the earliest)."""
    if not len(records):
        return records
    r = records.copy()
    r["_reg"] = pd.to_datetime(r.get("registration_date1"), errors="coerce", utc=True).dt.tz_localize(None)
    r["_comp"] = _completeness(r)
    first = r.groupby("email")["_reg"].transform("min")
    in_window = r["_reg"].isna() | first.isna() | (r["_reg"] <= first + pd.Timedelta(days=window_days))
    r = r[in_window].sort_values(["email", "_comp", "_reg"], ascending=[True, False, True])
    r = r.drop_duplicates("email", keep="first")
    return r.drop(columns=["_reg", "_comp"]).reset_index(drop=True)


def fetch_arrival_leads(emails: List[str], window_days: int = ARRIVAL_WINDOW_DAYS) -> pd.DataFrame:
    """Drop-in for fetch_leads_by_emails, but each lead is seen as at arrival."""
    return arrival_record(fetch_records(emails), window_days)

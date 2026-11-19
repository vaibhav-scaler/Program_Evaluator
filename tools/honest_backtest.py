"""
Honest backtest: how the tool does on months it had never seen.

For each cut-off month it trains a model only on the cohorts BEFORE that month (tools/train_recommender.py --asof), runs the tool with that model
on the learners of the later months, and counts which program sold was the primary, the fallback or the third row.
The live model is not touched. Results go to Database/honest_backtest.json, which the review workbook reads.

    python tools/honest_backtest.py                     # cut-offs: the last 3 mature months, one at a time (needs the lead cache)
    python tools/honest_backtest.py --cutoffs 2026-08,2026-10 --crm-cache Database/_crm_cache.pkl
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pandas as pd

import tools.build_review_workbook as B
import src.learned_recommender as lr
import src.evaluator as ev
from src.batch_processor import process_leads_dataframe

CRM_CACHE = os.path.join(ROOT, "Database", "_crm_cache.pkl")
OUT = os.path.join(ROOT, "Database", "honest_backtest.json")


def evaluate(model_path, W, leads, rates):
    lr._PATH = model_path; lr._MODEL = None
    res = {}
    for i in range(0, len(leads), 300):
        o, _ = process_leads_dataframe(leads.iloc[i:i + 300].reset_index(drop=True), include_export_df=False, index_offset=i)
        for x in o:
            res[str(x["person"]["email"]).lower()] = x
    g = []
    for r in W.itertuples():
        x = res.get(r.email)
        if not x or str(x["person"].get("normalized_persona", "")).startswith(("Student", "Postgraduate")):
            continue
        ac = (x.get("also_consider") or {}).get("catalog_code")
        b, p, f = r.program, x["primary"]["catalog_code"], x["fallback"]["catalog_code"]
        rp, rb = rates.get(p), rates.get(b)
        g.append(("primary" if b == p else "fallback" if b == f else "also" if b == ac else "none", bool(r.refunded), rp if rp is not None else rb, rb))
    G = pd.DataFrame(g, columns=["g", "r", "rp", "rb"]); n = len(G)
    return {"learners": n, "primary": int((G.g == "primary").sum()), "fallback": int((G.g == "fallback").sum()), "also": int((G.g == "also").sum()),
            "none": int((G.g == "none").sum()), "none_stayed": int(((G.g == "none") & ~G.r).sum()),
            "refunded": int(G.r.sum()), "refunded_primary": int(G[G.g == "primary"].r.sum()), "refunded_fallback": int(G[G.g == "fallback"].r.sum()),
            "refunded_also": int(G[G.g == "also"].r.sum()), "refunded_none": int(G[G.g == "none"].r.sum()),
            "expected_refunds_if_tool_primary_sold": round(float(G.rp.sum()), 1), "expected_refunds_for_what_sales_sold": round(float(G.rb.sum()), 1)}   # both use program refund rates from before the test months


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoffs", default=None, help="comma list YYYY-MM; the model is trained before each and tested on that month and the ones after (default: last 3 mature months)")
    ap.add_argument("--crm-cache", default=CRM_CACHE, help="lead records of all learners (made by tools/train_recommender.py)")
    ap.add_argument("--through", default=None, help="last cohort month to test on (default: the newest mature month)")
    ap.add_argument("--workbook", default=None)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    R = B.load_funnel(a.workbook or B.newest_workbook())
    mature = sorted(R.loc[R.mature == 1, "month"].dropna().unique())
    cutoffs = a.cutoffs.split(",") if a.cutoffs else mature[-3:]
    L = pd.read_pickle(a.crm_cache); L["email"] = L["email"].astype(str).str.lower(); L = L.drop_duplicates("email")
    results = []
    for c in cutoffs:
        months = [m for m in mature if m >= c and (not a.through or m <= a.through)]
        W = R[R.month.isin(months) & R.program.notna()].copy(); W["email"] = W.email.astype(str).str.lower()
        W = W[W.email.isin(set(L.email))]
        tmp = os.path.join(tempfile.mkdtemp(), "model_asof.json")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "train_recommender.py"), "--asof", c, "--model-out", tmp, "--crm-cache", a.crm_cache],
                       check=True, capture_output=True, cwd=ROOT)
        leads = L[L.email.isin(set(W.email))].reset_index(drop=True)
        rates = {p: r for p, r, _n, _s in B.program_rates(R, months[0])}          # program refund rates from cohorts before the test months
        row = {"trained_before": c, "tested_on": months, **evaluate(tmp, W, leads, rates)}
        results.append(row)
        n = row["learners"]
        print(f"trained before {c}, tested on {months[0]} to {months[-1]}: {n} learners | primary {100 * row['primary'] / n:.1f}% | primary or fallback {100 * (row['primary'] + row['fallback']) / n:.1f}% | with third row {100 * (n - row['none']) / n:.1f}%")
    json.dump({"note": "Each model was trained only on cohorts before the cut-off, then run on later months it had never seen.", "results": results}, open(a.out, "w"), indent=1)
    print("saved", a.out)


if __name__ == "__main__":
    main()

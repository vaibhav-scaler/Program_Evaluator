"""
The monthly routine, in the right order. Run it once the new cohort months have closed their refund window.

  1. REVIEW   the newest cohorts against the CURRENT model (the new months are new to it, so this is a fair test): coverage, refunds,
              FDE numbers, is the stated confidence still honest
  2. MATRIX   rebuild the refund matrix and learner outcomes from the refund funnel
  3. RETRAIN  retrain the recommender on every learner (newer months count more, so FDE is learned from its recent sales) and
              recalibrate the confidence on months it had not seen
  4. WORKBOOK rebuild the live review workbook with the new model

Before you start: download the newest refund funnel workbook into Database/ (Refunds Funnel (N).xlsx).
Needs the METABASE_* variables. Restart the app afterwards so it loads the new model.

    python tools/monthly_refresh.py
    python tools/monthly_refresh.py --months 2026-09,2026-10,2026-11 --skip-workbook
"""
import argparse
import datetime
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def run(title, cmd, log):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}", flush=True)
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        if "Warning" in line or "warnings.warn" in line:
            continue
        print(line, end="", flush=True)
        log.write(line)
    p.wait()
    if p.returncode:
        raise SystemExit(f"step failed: {title}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", default=None, help="cohort months to review and show in the workbook (default: the last 3 mature months)")
    ap.add_argument("--skip-review", action="store_true")
    ap.add_argument("--skip-train", action="store_true")
    ap.add_argument("--skip-workbook", action="store_true")
    a = ap.parse_args()
    os.makedirs(os.path.join(ROOT, "output"), exist_ok=True)
    stamp = datetime.date.today().isoformat()
    cache_leads = os.path.join(ROOT, "Database", "_review_leads.pkl")
    cache_crm = os.path.join(ROOT, "Database", "_crm_cache.pkl")
    mflag = ["--months", a.months] if a.months else []
    with open(os.path.join(ROOT, "output", f"monthly_refresh_{stamp}.log"), "w") as log:
        if os.path.exists(cache_leads):
            os.remove(cache_leads)                       # always download the leads fresh
        if not a.skip_review:
            run("1. REVIEW the newest cohorts with the current model", [PY, "tools/monthly_review.py", *mflag, "--cache", cache_leads], log)
        if not a.skip_train:
            run("2. MATRIX: rebuild the refund matrix and learner outcomes", [PY, "-m", "src.clean_matrix_pipeline"], log)
            run("3. RETRAIN the recommender and recalibrate the confidence", [PY, "tools/train_recommender.py", "--crm-cache", cache_crm, "--refresh-crm"], log)
        if not a.skip_train:
            run("3b. HONEST BACKTEST: how the tool does on months it had never seen", [PY, "tools/honest_backtest.py", "--crm-cache", cache_crm], log)
        if not a.skip_workbook:
            run("4. WORKBOOK: rebuild the live review workbook with the new model", [PY, "tools/build_review_workbook.py", *mflag, "--cache", cache_leads], log)
    print(f"\nDone. The log is in output/monthly_refresh_{stamp}.log. Restart the app so it loads the new model.")


if __name__ == "__main__":
    main()

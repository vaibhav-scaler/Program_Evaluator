"""
Monthly check of the recommendations against what sales actually sold and what happened.

For learners in the Raw sheet of the refund funnel it asks, for the newest mature cohorts:
  * was the program sold the tool's primary, its fallback, or its "also consider" pick, and how many refunded in each group
  * how each program is doing, with FDE (Program 3) in its own section while its share of sales is still moving
  * is the stated confidence still honest (stated against what happened)
  * is anything drifting month by month

Needs Metabase access (METABASE_* variables) to fetch each learner's lead record, as the tool does at lookup.
(Students the tool identifies are left out: they go to the prerequisite gate, not to a program.)

    python tools/monthly_review.py                               # last 3 mature cohort months
    python tools/monthly_review.py --months 2026-08,2026-09,2026-10 --cache Database/_review_leads.pkl
"""
import argparse
import math
import os
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np
import pandas as pd

import tools.build_review_workbook as B

CODE = {"P1_ACADEMY": "Program 1", "P2_DSML": "Program 2", "P3_FDE": "Program 3", "P4_AIML_AGENTIC": "Program 4", "P5_DEVOPS_CLOUD": "Program 5"}
PROGS = ["Program 1", "Program 2", "Program 3", "Program 4", "Program 5"]
LABEL = {"Program 1": "Academy", "Program 2": "DSML", "Program 3": "FDE", "Program 4": "AI/ML", "Program 5": "DevOps"}


def z_test(k1, n1, k2, n2):
    if min(n1, n2) == 0:
        return float("nan")
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return (k1 / n1 - k2 / n2) / se if se else 0.0


def pc(v):
    return "-" if v != v else f"{100 * v:.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook", default=None)
    ap.add_argument("--months", default=None, help="comma list YYYY-MM; default = the last 3 mature months")
    ap.add_argument("--cache", default=None, help="pickle file for the downloaded leads; reused if it exists")
    ap.add_argument("--out", default=os.path.join(ROOT, "Database", "monthly_review.csv"))
    a = ap.parse_args()

    R = B.load_funnel(a.workbook or B.newest_workbook())
    mature = sorted(R.loc[R.mature == 1, "month"].dropna().unique())
    months = a.months.split(",") if a.months else mature[-3:]
    W = R[R.month.isin(months) & R.program.notna() & (R.mature == 1)].copy()
    print(f"reviewing {len(W)} learners of the five programs, cohorts {months[0]} to {months[-1]}")
    emails = sorted({e for e in list(W.email) + [x for x in W.lead_email if x != "nan"]})
    L = B.fetch_leads(emails, a.cache)
    df = B.build_rows(W, L)
    df = df[~df.persona.astype(str).str.startswith(("Student", "Postgraduate"))].copy()
    df["month"] = df.month.str.replace("Cohort ", "", regex=False)
    df["enq"] = df.enq.map(CODE)
    df["r"] = (df.refunded_txt == "Yes").astype(int)
    E = df[df.found == "Yes"].copy()
    E["group"] = np.where(E.bought == E.prim, "primary", np.where(E.bought == E.fall, "fallback", np.where(E.bought == E.also, "also consider", "none of the three")))
    n = len(E)
    print(f"learners matched to a Metabase lead and evaluated: {n} of {len(W)}\n")

    print("=== 1. WAS THE PROGRAM SOLD ONE THE TOOL SHOWED? ===")
    print(f"{'program sold was the tool':28}{'learners':>9}{'share':>8}{'refunded':>10}{'rate':>8}")
    for g in ("primary", "fallback", "also consider", "none of the three"):
        s = E[E.group == g]
        print(f"{g:28}{len(s):9d}{100 * len(s) / n:7.0f}%{int(s.r.sum()):10d}{100 * s.r.mean() if len(s) else float('nan'):7.1f}%")
    two = E[E.group.isin(["primary", "fallback"])]
    print(f"\nprimary or fallback covers {100 * len(two) / n:.1f}% | with 'also consider' {100 * (len(two) + (E.group == 'also consider').sum()) / n:.1f}%")
    pr, ot = E[E.group == "primary"], E[E.group != "primary"]
    print(f"refund: bought the primary {pc(pr.r.mean())} vs everyone else {pc(ot.r.mean())} (z = {z_test(ot.r.sum(), len(ot), pr.r.sum(), len(pr)) * -1:.1f})")

    print("\n=== 2. BY PROGRAM SOLD ===")
    print(f"{'program':14}{'learners':>9}{'share of sales':>16}{'primary right':>15}{'primary or fallback':>21}{'with also':>11}{'refund rate':>13}")
    for p in PROGS:
        s = E[E.bought == p]
        if not len(s):
            continue
        two_ = (s.group.isin(["primary", "fallback"])).mean(); three = (s.group != "none of the three").mean()
        print(f"{p + ' ' + LABEL[p]:14}{len(s):9d}{100 * len(s) / n:15.0f}%{100 * (s.group == 'primary').mean():14.0f}%{100 * two_:20.0f}%{100 * three:10.0f}%{100 * s.r.mean():12.1f}%")

    print("\n=== 3. FDE (PROGRAM 3), WHILE ITS SHARE OF SALES IS STILL MOVING ===")
    F = E[E.bought == "Program 3"].copy()
    print("by cohort month:  FDE share of sales | shown as primary or fallback | FDE buyers covered (primary or fallback / with also) | FDE refund rate")
    for m, g in E.groupby("month"):
        f = g[g.bought == "Program 3"]
        shown = ((g.prim == "Program 3") | (g.fall == "Program 3")).mean()
        print(f"  {m}:  {100 * len(f) / len(g):4.0f}% | {100 * shown:4.0f}% | " + (f"{100 * f.group.isin(['primary', 'fallback']).mean():3.0f}% / {100 * (f.group != 'none of the three').mean():3.0f}% (n={len(f)}) | {pc(f.r.mean())}" if len(f) else "no FDE sales"))
    if len(F):
        F["signal"] = np.where((F.enq == "Program 3") | (F.team == "FDE team"), "FDE enquiry or FDE team", "no FDE signal (sales cross-sell)")
        print("\nFDE buyers with and without an FDE signal in the lead data:")
        for s, g in F.groupby("signal"):
            print(f"  {s:34}{len(g):4d} ({100 * len(g) / len(F):3.0f}% of FDE buyers) | primary {100 * (g.group == 'primary').mean():3.0f}% | primary or fallback {100 * g.group.isin(['primary', 'fallback']).mean():3.0f}% | with also {100 * (g.group != 'none of the three').mean():3.0f}%")
        print("  FDE buyers by what they enquired about:", F.enq.value_counts().to_dict())
        print("  what the tool showed first for the FDE buyers it missed:", F[F.group == "none of the three"].prim.value_counts().to_dict())
    shown_primary = E[E.prim == "Program 3"]
    if len(shown_primary):
        print(f"  when the tool shows FDE first ({len(shown_primary)} leads) it is bought {100 * (shown_primary.bought == 'Program 3').mean():.0f}% of the time")

    try:
        import json as _json
        trained_through = _json.load(open(os.path.join(ROOT, "src", "models", "learned_recommender.json"))).get("trained_through")
    except Exception:
        trained_through = None
    new_months = [m for m in months if trained_through and m > trained_through]
    print("\n=== 4. IS THE STATED CONFIDENCE STILL HONEST? (stated against what happened) ===")
    if trained_through:
        print(f"  the model was last trained through {trained_through}; months after that are new to it: {new_months or 'none of the months reviewed'}")
    E["conf_p"] = pd.to_numeric(E.conf_p, errors="coerce"); E["conf_f"] = pd.to_numeric(E.conf_f, errors="coerce")
    print(f"  first program: stated {E.conf_p.mean():.1f}% | actually bought {100 * (E.group == 'primary').mean():.1f}%")
    print(f"  second program: stated {E.conf_f.mean():.1f}% | actually bought {100 * (E.group == 'fallback').mean():.1f}%")
    fresh = E[E.month.isin(new_months)] if new_months else E.iloc[0:0]
    if len(fresh) >= 100:
        drift = pd.to_numeric(fresh.conf_p, errors="coerce").mean() - 100 * (fresh.group == "primary").mean()
        print(f"  on the new months only ({len(fresh)} learners): stated {pd.to_numeric(fresh.conf_p, errors='coerce').mean():.1f}% vs bought {100 * (fresh.group == 'primary').mean():.1f}%")
        print("  " + ("OK: within 7 points." if abs(drift) <= 7 else f"CHECK: {drift:+.1f} points apart. Recalibrate: run tools/monthly_refresh.py"))
    else:
        print("  not a fair test: these months were already in the model's training data, so the tool looks better here than it will on new leads.")
        print("  Run this review BEFORE retraining (tools/monthly_refresh.py does that), so the newest months are new to the model.")

    print("\n=== 5. MONTH BY MONTH ===")
    print(f"{'cohort':10}{'learners':>9}{'primary':>9}{'primary or fallback':>21}{'with also':>11}{'refund rate':>13}")
    for m, g in E.groupby("month"):
        print(f"{m:10}{len(g):9d}{100 * (g.group == 'primary').mean():8.0f}%{100 * g.group.isin(['primary', 'fallback']).mean():20.0f}%{100 * (g.group != 'none of the three').mean():10.0f}%{100 * g.r.mean():12.1f}%")

    E[["month", "bought", "prim", "fall", "also", "group", "r", "enq", "team", "persona"]].to_csv(a.out, index=False)
    print(f"\nrow-level results (no emails) saved to {a.out}. Retrain with tools/monthly_refresh.py when coverage falls, the confidence drifts, or FDE's share keeps moving.")


if __name__ == "__main__":
    main()

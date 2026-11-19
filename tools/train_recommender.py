"""
Retrain the learned program ranking (src/models/learned_recommender.json) from the refund funnel and Metabase.

What it builds
  * an enrolment model: which program a lead like this is likely to take (from the pre-sale Metabase lead record)
  * the refund rate of each program and of each batch level, from the Raw sheet
  * an out-of-time check, trained on early cohorts and judged on later ones, whose numbers are written into the JSON

Needs scikit-learn (NOT a run-time dependency) and Metabase access (METABASE_* variables) unless a cache file is given.

    pip install scikit-learn
    python tools/train_recommender.py                              # newest workbook in Database/
    python tools/train_recommender.py --workbook "Database/Refunds Funnel (2).xlsx" --crm-cache Database/_crm_cache.pkl
"""
import argparse
import json
import math
import os
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression

from src.learned_recommender import base_features, role_words

ENR = {"academy": "P1", "dsml": "P2", "fde": "P3", "aiml": "P4", "devops": "P5"}


def newest_workbook():
    for n in ("Refunds Funnel (2).xlsx", "Refunds Funnel (1).xlsx"):
        p = os.path.join(ROOT, "Database", n)
        if os.path.exists(p):
            return p
    raise SystemExit("No refund funnel workbook found in Database/.")


def load_learners(path):
    R = pd.read_excel(path, sheet_name="Raw").drop_duplicates("User Id").copy()
    R["email"] = R["Email"].astype(str).str.strip().str.lower()
    R["lead_email"] = R["Lead Email"].astype(str).str.strip().str.lower()
    R["refunded"] = (R["Refunded"].astype(str).str.strip().str.lower() == "true").astype(int)      # the funnel's own Refunded column
    cm = pd.to_datetime(R["Refunds Oms Cohort"], errors="coerce")
    R["mature"] = (cm < cm.max()).astype(int)
    R["cohort_m"] = cm.dt.strftime("%Y-%m")
    R["enrolled"] = R["Intake Program"].astype(str).str.strip().str.lower().map(ENR)
    return R[R.enrolled.notna()]


def load_crm(R, cache, refresh=False):
    """The lead of every learner AS SEEN ON ARRIVAL (src/arrival_view.py), not the record created at the sale.
    Learners are matched by their own email, else by the Lead Email the refund funnel records."""
    if cache and os.path.exists(cache) and not refresh:
        C = pd.read_pickle(cache)
        C["email"] = C["email"].astype(str).str.lower()
        return C.drop_duplicates("email")
    from src.arrival_view import fetch_arrival_leads
    own = set(R.email); alt = {x for x in R.lead_email if x and x != "nan"}
    L = fetch_arrival_leads(sorted(own | alt)).drop_duplicates("email").set_index("email", drop=False)
    rows = []
    for r in R.itertuples():
        key = r.email if r.email in L.index else (r.lead_email if r.lead_email in L.index else None)
        if key is not None:
            d = L.loc[key].to_dict(); d["email"] = r.email; rows.append(d)
    C = pd.DataFrame(rows)
    if cache:
        C.to_pickle(cache)
    return C


def rolling_forecasts(B, y, cm, recency):
    """For each month, train on EARLIER months only and score that month. Returns (pairs, leads): pairs = (month, chance, bought) for every
    lead and program; leads = (month, chance of the top pick, top pick bought, chance of the 2nd pick, 2nd bought). These are honest
    out-of-time numbers, which is what a new lead will get."""
    months = sorted(set(cm)); idx = {m: i for i, m in enumerate(months)}; pairs, leads = [], []
    for k in range(2, len(months)):
        m = months[k]; tr = np.array([c < m for c in cm]); te = np.where(cm == m)[0]
        dv = DictVectorizer(); X = dv.fit_transform([B[i] for i in np.where(tr)[0]])
        w = np.array([math.exp(recency * (idx[cm[i]] - idx[months[k - 1]])) for i in np.where(tr)[0]])
        mdl = LogisticRegression(max_iter=4000, C=0.5).fit(X, y[tr], sample_weight=w); cls = list(mdl.classes_)
        P = mdl.predict_proba(dv.transform([B[i] for i in te]))
        for r, i in enumerate(te):
            for j, c in enumerate(cls):
                pairs.append((m, float(P[r, j]), int(y[i] == c)))
            o = np.argsort(-P[r])
            leads.append((m, float(P[r, o[0]]), int(cls[o[0]] == y[i]), float(P[r, o[1]]), int(cls[o[1]] == y[i])))
    return pairs, leads


def fit_calibration(pairs):
    """Chance the model gives a program -> how often that program was really bought (isotonic, so it never goes down as the chance goes up)."""
    x = np.array([p for _m, p, _h in pairs]); h = np.array([hh for _m, _p, hh in pairs])
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(x, h)
    grid = np.linspace(0, 1, 101)
    return {"x": [round(float(g), 2) for g in grid], "y": [round(float(v), 4) for v in iso.predict(grid)], "pairs": int(len(pairs))}, iso


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook", default=None)
    ap.add_argument("--crm-cache", default=None)
    ap.add_argument("--refresh-crm", action="store_true", help="download every lead again even if the cache file exists (use this each month)")
    ap.add_argument("--test-from", default=None, help="first cohort month (YYYY-MM) of the out-of-time test; default = the last mature month")
    ap.add_argument("--asof", default=None, help="train ONLY on cohorts before this month (YYYY-MM) and save to --model-out: a model as it stood then, for honest backtests")
    ap.add_argument("--model-out", default=None, help="where to save the model (default: src/models/learned_recommender.json; required with --asof)")
    ap.add_argument("--recency", type=float, default=0.35, help="weight of newer cohorts: each later month counts exp(recency) times more (0 = equal weight)")
    a = ap.parse_args()
    R = load_learners(a.workbook or newest_workbook())
    C = load_crm(R, a.crm_cache, refresh=a.refresh_crm)
    D = R.merge(C, on="email", how="inner", suffixes=("_r", "")).reset_index(drop=True)
    print(f"learners with a Metabase lead record: {len(D)} | mature: {int(D.mature.sum())}")
    cnt = {}
    for rl in D["role"]:
        for t in set(role_words(rl)):
            cnt[t] = cnt.get(t, 0) + 1
    role_vocab = sorted(t for t, c in cnt.items() if c >= 25)            # role-title words seen at least 25 times
    B = [base_features(r, today_year=2026, role_vocab=role_vocab) for r in D.to_dict("records")]
    y_enr = D.enrolled.values; y_ref = D.refunded.values.astype(int); mature = D.mature.values == 1; cm = D.cohort_m.values

    # ---- out-of-time check
    months = sorted({m for m in cm[mature]})
    if a.asof and not a.model_out:
        raise SystemExit("--asof needs --model-out so the live model is not overwritten")
    test_from = a.asof or a.test_from or months[-1]
    all_months = sorted(set(cm)); midx = {m: i for i, m in enumerate(all_months)}
    def weights(idx, ref_month):
        # newer cohorts count more: a program launched recently (FDE) is learned from its recent sales, not diluted by older months
        return np.array([math.exp(a.recency * (midx[cm[i]] - midx[ref_month])) for i in idx])
    train = np.array([m < test_from for m in cm]); test = np.array([(m >= test_from and m in months) for m in cm])
    last_train = max(m for m in all_months if m < test_from)
    dv = DictVectorizer(); X = dv.fit_transform([B[i] for i in np.where(train)[0]])
    me = LogisticRegression(max_iter=4000, C=0.5).fit(X, y_enr[train], sample_weight=weights(np.where(train)[0], last_train))
    cls = list(me.classes_); te = np.where(test & np.isin(y_enr, cls))[0]
    P = me.predict_proba(dv.transform([B[i] for i in te])); ei = np.array([cls.index(p) for p in y_enr[te]]); yr = y_ref[te]
    tr_m = np.where(train & mature)[0]
    rate = np.array([y_ref[tr_m][y_enr[tr_m] == c].mean() for c in cls])
    order = []
    for i in range(len(te)):
        by_p = np.argsort(-P[i]); pool = [j for j in by_p[:3] if P[i, j] >= 0.5 * P[i, by_p[0]]]; pool.sort(key=lambda j: rate[j]); order.append(pool + [j for j in by_p if j not in pool])
    prim = np.array([o[0] for o in order]); fall = np.array([o[1] for o in order])
    top1 = P.argmax(1)
    ag = prim == ei; df_ = ~ag; ra, rd = yr[ag].mean(), yr[df_].mean(); se = math.sqrt(ra * (1 - ra) / ag.sum() + rd * (1 - rd) / df_.sum())
    ev = {"split": f"trained on cohorts before {test_from}, tested on {test_from} and later (mature cohorts)", "test_learners": int(len(te)),
          "sold_program_in_top1": round(float(np.mean(top1 == ei)), 3), "sold_program_in_top2": round(float(np.mean([ei[i] in np.argsort(-P[i])[:2] for i in range(len(te))])), 3),
          "sold_program_in_top3": round(float(np.mean([ei[i] in np.argsort(-P[i])[:3] for i in range(len(te))])), 3),
          "fde_buyers_in_primary_or_fallback": (round(float(np.mean([(cls[prim[i]] == "P3") or (cls[fall[i]] == "P3") for i in range(len(te)) if cls[ei[i]] == "P3"])), 3) if "P3" in cls and any(cls[e] == "P3" for e in ei) else None),
          "recency_weight": a.recency,
          "policy_used": {"rule": "top 3 most likely, at least half as likely as the best, lowest refund rate first",
                          "sold_program_is_primary": round(float(ag.mean()), 3), "sold_program_in_primary_or_fallback": round(float(np.mean((prim == ei) | (fall == ei))), 3),
                          "refund_when_sold_equals_primary": round(float(ra), 4), "refund_when_different": round(float(rd), 4), "z": round(float((rd - ra) / se), 2)}}
    print(json.dumps(ev, indent=1))

    # ---- final model on every learner
    _fit = np.where(train)[0] if a.asof else np.arange(len(D))             # --asof: only what was known before that month
    _ref = last_train if a.asof else all_months[-1]
    dv = DictVectorizer(); X = dv.fit_transform([B[i] for i in _fit])
    me = LogisticRegression(max_iter=4000, C=0.5).fit(X, y_enr[_fit], sample_weight=weights(_fit, _ref))
    M = R[(R.mature == 1) & ((R.cohort_m < a.asof) if a.asof else True)]   # refund history uses EVERY mature learner in the Raw sheet, not only those matched to a Metabase lead
    prog = {p: {"refund_rate": round(float(g.refunded.mean()), 4), "n": int(len(g))} for p, g in M.groupby("enrolled")}
    batch = {}
    if "Batch Persona New" in M.columns:
        for (p, b), g in M[M["Batch Persona New"].notna()].groupby(["enrolled", "Batch Persona New"]):
            batch.setdefault(p, {})[b] = {"refund_rate": round(float(g.refunded.mean()), 4), "n": int(len(g))}
    # ---- measured confidence: how often the model's pick is right, learned only from months it had not seen
    pairs, leads = rolling_forecasts([B[i] for i in _fit], y_enr[_fit], cm[_fit], a.recency)
    cal, _ = fit_calibration(pairs)
    cal_months = sorted({m for m, _p, _h in pairs})
    # honest check: calibrate on months before test_from, then see how well the stated chance matches what happened afterwards
    early = [t for t in pairs if t[0] < test_from]; later = [t for t in leads if t[0] >= test_from]
    check = None
    if len(early) > 500 and len(later) > 100:
        _c, iso_e = fit_calibration(early)
        p1 = iso_e.predict(np.array([t[1] for t in later])); h1 = np.array([t[2] for t in later]); p2 = iso_e.predict(np.array([t[3] for t in later])); h2 = np.array([t[4] for t in later])
        raw1 = np.array([t[1] for t in later])
        bins = [(0, 0.45), (0.45, 0.6), (0.6, 0.75), (0.75, 1.01)]
        rows_ = [{"stated_range": f"{int(lo*100)}-{int(min(hi,1)*100)}%", "leads": int(((p1 >= lo) & (p1 < hi)).sum()), "stated": round(float(p1[(p1 >= lo) & (p1 < hi)].mean()), 3), "actual": round(float(h1[(p1 >= lo) & (p1 < hi)].mean()), 3)} for lo, hi in bins if ((p1 >= lo) & (p1 < hi)).sum() >= 10]
        check = {"calibrated_on_months_before": test_from, "leads_checked": int(len(later)), "first_program_stated_avg": round(float(p1.mean()), 3), "first_program_actual": round(float(h1.mean()), 3),
                 "second_program_stated_avg": round(float(p2.mean()), 3), "second_program_actual": round(float(h2.mean()), 3), "raw_model_chance_avg": round(float(raw1.mean()), 3), "by_range": rows_}
        print("measured-confidence check on months not used to calibrate:"); print(json.dumps(check, indent=1))
    out = {"enrol": {"classes": list(me.classes_), "features": dv.feature_names_, "coef": me.coef_.round(4).tolist(), "intercept": me.intercept_.round(4).tolist()},
           "program_refund": prog, "batch_refund": batch, "policy_k": 3, "role_vocab": role_vocab, "calibration": cal, "trained_through": (last_train if a.asof else all_months[-1]),
           "evaluation": {"trained_on": int(len(D)), "out_of_time": ev,
                          "note": "Program refund differences held from the training months to the test months. A lead-level refund model did not, so it is not used.",
                          "calibration_check": check, "calibration_months": cal_months}}
    path = a.model_out or os.path.join(ROOT, "src", "models", "learned_recommender.json")
    json.dump(out, open(path, "w"))
    print("saved", path)


if __name__ == "__main__":
    main()

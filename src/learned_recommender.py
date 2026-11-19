"""
Learned program ranking from the refund funnel and the Metabase lead record.

What is learned from enrolled learners, using only what is known BEFORE the sale:
  1. an enrolment model: how likely a lead like this is to take each program (so primary and fallback are programs sales can really sell)
  2. the refund rate of each program in the refund funnel

The ranking takes the programs the lead is most likely to take and puts the one with the lowest refund rate first.
(A lead-level refund model was tried and dropped: it did not hold on later cohorts. The program-level differences did.)
Weights live in models/learned_recommender.json (no extra libraries needed at run time). If the file is missing the tool falls
back to its rule-based ranking.
"""
import datetime
import json
import math
import os
import re
from typing import Any, Dict, List, Optional

from .role_taxonomy import classify_role

PROGRAMS = ("P1", "P2", "P3", "P4", "P5")
CODE_TO_P = {"P1_ACADEMY": "P1", "P2_DSML": "P2", "P3_FDE": "P3", "P4_AIML_AGENTIC": "P4", "P5_DEVOPS_CLOUD": "P5"}
P_TO_CODE = {v: k for k, v in CODE_TO_P.items()}
_PATH = os.path.join(os.path.dirname(__file__), "models", "learned_recommender.json")
_MODEL: Optional[Dict[str, Any]] = None
REFUND_TIE_MARGIN = 0.03      # refund rates closer than 3 points are treated as equal
STATED_PROMOTE_MIN = 1.1      # off: the first two programs go purely by the data. The lead's own enquiry is shown in 'Also consider' instead (evaluator._add_also_consider).
                              # On honest data this keeps top-two coverage at 81.0% (78.9% when the enquiry was pushed into the second slot) and still shows the enquiry to 98.8% of leads.
_NA = {"", "none", "nan", "not applicable", "not applicable account", "na", "n/a", "self employed", "freelancer"}


def _load() -> Dict[str, Any]:
    global _MODEL
    if _MODEL is None:
        try:
            with open(_PATH, encoding="utf-8") as f:
                m = json.load(f)
            m["enrol"]["index"] = {n: i for i, n in enumerate(m["enrol"]["features"])}
            _MODEL = m
        except Exception:
            _MODEL = {}
    return _MODEL


def available() -> bool:
    return bool(_load())


def calibration_available() -> bool:
    c = _load().get("calibration") if _load() else None
    return bool(c and c.get("x") and c.get("y"))


def calibrated(p: float) -> float:
    """The model's chance for a program -> how often such a program was really bought on months the model had not seen."""
    c = _load().get("calibration") or {}
    xs, ys = c.get("x") or [], c.get("y") or []
    if not xs:
        return float(p)
    p = max(0.0, min(1.0, float(p)))
    for i in range(1, len(xs)):
        if p <= xs[i]:
            x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
            return y0 if x1 == x0 else y0 + (y1 - y0) * (p - x0) / (x1 - x0)
    return float(ys[-1])


def model_info() -> Dict[str, Any]:
    m = _load()
    return m.get("evaluation", {}) if m else {}


def _toks(s) -> List[str]:
    return [t for t in re.split(r"[^a-z0-9]+", str(s or "").lower()) if len(t) > 2 and not t.isdigit()][:8]


def _bin(v, edges):
    try:
        v = float(v)
    except Exception:
        return "na"
    if v != v:
        return "na"
    for i, e in enumerate(edges):
        if v < e:
            return str(i)
    return str(len(edges))


_ROLE_STOP = {"and", "the", "of", "for", "in", "at", "an", "to", "with", "sr", "jr", "senior", "junior", "lead", "associate", "executive", "officer"}


def role_words(role) -> List[str]:
    return sorted({t for t in re.split(r"[^a-z]+", str(role or "").lower()) if len(t) > 2 and t not in _ROLE_STOP})


def base_features(lead: Dict[str, Any], today_year: Optional[int] = None, role_vocab=None) -> Dict[str, float]:
    """Pre-sale features of one lead. The same function builds the training rows."""
    f: Dict[str, float] = {}
    vocab = set(role_vocab) if role_vocab is not None else set(_load().get("role_vocab", []))

    def cat(k, v):
        v = str(v if v is not None else "").strip().lower()
        f[f"{k}={v if v not in ('nan', 'none', '') else 'missing'}"] = 1.0

    for k in ("program_type", "which_bda_team", "company_type", "event_type", "utm_source", "country_type"):
        cat(k, lead.get(k))
    # The BDA team field lists every team that handled the lead ("fde / Academy"): use each team and the first one as features,
    # so a combination seen once still tells the model which teams were involved.
    teams = [t.strip() for t in str(lead.get("which_bda_team") or "").split("/") if t.strip()]
    for t in teams:
        f["team:" + t] = 1.0
    if teams:
        f["team1:" + teams[0]] = 1.0
    f["nteams=%d" % min(len(teams), 3)] = 1.0
    for t in _toks(lead.get("event_name")):
        f["ev:" + t] = 1.0
    for t in _toks(re.sub(r"https?://[^/]+", "", str(lead.get("landing_page_url") or ""))):
        f["lp:" + t] = 1.0
    key, _ = classify_role(lead.get("role"))
    f["role=%s" % key] = 1.0
    org = str(lead.get("orgname") or "").strip().lower()
    f["org_blank" if org in _NA else "org_given"] = 1.0
    try:
        gap = (today_year or datetime.date.today().year) - int(float(lead.get("orgyear")))
        f["yrgap=%d" % (min(max(gap, 0), 20) // 2 * 2)] = 1.0
    except Exception:
        f["yrgap=missing"] = 1.0
    f["set_passed=%s" % lead.get("test_passed_flag")] = 1.0
    # the words of the role title (the persona label alone loses them) and how the lead engaged with the event (attendance only exists before payment)
    for t in role_words(lead.get("role")):
        if t in vocab:
            f["rt:" + t] = 1.0
    f["attended=%s" % (str(lead.get("attended")).strip().lower() in ("1", "1.0", "true"))] = 1.0
    f["min=%s" % _bin(lead.get("minutes_in_event"), [1, 15, 30, 60, 120])] = 1.0
    f["evrank=%s" % _bin(lead.get("event_rank_registraion"), [2, 4, 8, 16])] = 1.0
    return f


def _dot(part: Dict[str, Any], feats: Dict[str, float], ci: Optional[int] = None) -> float:
    s = part["intercept"][ci] if ci is not None else part["intercept"]
    coef = part["coef"][ci] if ci is not None else part["coef"]
    for name, v in feats.items():
        j = part["index"].get(name)
        if j is not None:
            s += coef[j] * v
    return s


def predict(lead: Dict[str, Any]) -> Optional[Dict[str, Dict[str, float]]]:
    """For each program: {'enrol': probability the lead takes it, 'refund': that program's historical refund rate}."""
    m = _load()
    if not m:
        return None
    base = base_features(lead)
    scores = [_dot(m["enrol"], base, i) for i in range(len(m["enrol"]["classes"]))]
    mx = max(scores)
    ex = [math.exp(s - mx) for s in scores]
    tot = sum(ex)
    rates = m.get("program_refund", {})
    return {cls: {"enrol": e / tot, "refund": float(rates.get(cls, {}).get("refund_rate", 0.22))} for cls, e in zip(m["enrol"]["classes"], ex)}


def program_history(code: str) -> Optional[Dict[str, Any]]:
    m = _load()
    r = (m.get("program_refund") or {}).get(CODE_TO_P.get(code, ""))
    return dict(r) if r else None


_LABEL = {"P1": "Academy", "P2": "Data Science & ML", "P3": "FDE", "P4": "AI & ML (Agentic AI)", "P5": "DevOps & Cloud"}


def all_programs_history() -> List[Dict[str, Any]]:
    """Refund rate and size of every program in the refund funnel, with the overall rate."""
    m = _load()
    rates = m.get("program_refund") or {}
    return [{"code": P_TO_CODE[p], "program": p, "label": _LABEL[p], "rate": v["refund_rate"], "n": v["n"]} for p, v in sorted(rates.items()) if p in _LABEL]


def overall_refund() -> Optional[float]:
    rows = all_programs_history()
    tot = sum(r["n"] for r in rows)
    return round(sum(r["rate"] * r["n"] for r in rows) / tot, 4) if tot else None


def batch_history(code: str) -> Dict[str, Any]:
    m = _load()
    return dict((m.get("batch_refund") or {}).get(CODE_TO_P.get(code, ""), {}))


def rank(lead: Dict[str, Any], allowed: List[str], stated: Optional[str] = None, k: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
    """
    allowed: program codes the rules allow for this lead (for example P1_ACADEMY).
    1. Take the k most likely programs among them (k = 3).
    2. Keep those at least half as likely as the best one, so only programs sales can realistically sell compete.
    3. Put the one with the lowest refund rate first. The rest follow by likelihood.
    4. A stated interest that is not in the first two, and is at least 15% as likely as the best, is brought in as the fallback.
    Tested on later cohorts this keeps 83% of sold programs inside primary or fallback while shifting the primary to lower-refund programs.
    """
    pred = predict(lead)
    if not pred:
        return None
    m = _load()
    k = k or int(m.get("policy_k", 3))
    cands = [(CODE_TO_P[c], c) for c in allowed if c in CODE_TO_P]
    if not cands:
        return None
    cands.sort(key=lambda pc: -pred[pc[0]]["enrol"])
    best = pred[cands[0][0]]["enrol"]
    pool = [pc for pc in cands[:k] if pred[pc[0]]["enrol"] >= 0.5 * best]
    # Lower refund rate goes first, but only when it is lower by more than REFUND_TIE_MARGIN. Programs within a few points of each other
    # are a tie (the rates are estimates from a few hundred learners), and a tie keeps the order of likelihood to be bought.
    ordered = []
    for pc in pool:                                   # the pool arrives in order of likelihood
        pos = len(ordered)
        while pos > 0 and pred[pc[0]]["refund"] + REFUND_TIE_MARGIN <= pred[ordered[pos - 1][0]]["refund"]:
            pos -= 1
        ordered.insert(pos, pc)
    pool = ordered
    order = pool + [pc for pc in cands if pc not in pool]
    if stated in CODE_TO_P and len(order) >= 2:
        sp = CODE_TO_P[stated]
        if any(p == sp for p, _ in cands) and sp not in [p for p, _ in order[:2]] and pred[sp]["enrol"] >= STATED_PROMOTE_MIN * best:
            order = [order[0], (sp, stated)] + [x for x in order[1:] if x[0] != sp]
    return [{"code": c, "program": p, "enrol": round(pred[p]["enrol"], 4), "refund": round(pred[p]["refund"], 4)} for p, c in order]

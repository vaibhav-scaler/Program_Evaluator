"""
Work-experience band for a lead who gave no experience, only a graduation or employer year.

Years since graduation overstates experience (people change careers, take breaks), so this small model, trained on enrolled
learners' reported experience, corrects it. On held-out learners it picks the right band 71% of the time against 64% for the
plain years-since-graduation estimate, and overstates by a band or more 23% of the time against 33%.
Weights live in models/experience_band.json (no extra libraries needed at run time).
"""
import json
import math
import os
from typing import Optional

_PATH = os.path.join(os.path.dirname(__file__), "models", "experience_band.json")
_MODEL = None
_BAND_KEY = {"0-1": "EXP_0_1", "1-3": "EXP_1_3", "3-5": "EXP_3_5", "5+": "EXP_5_PLUS"}
_PROG = {"academy": "academy", "data_science": "dsml", "devops": "devops", "ai_ml": "aiml", "fde": "fde"}


def _load():
    global _MODEL
    if _MODEL is None:
        try:
            with open(_PATH, encoding="utf-8") as f:
                m = json.load(f)
            m["index"] = {name: i for i, name in enumerate(m["features"])}
            _MODEL = m
        except Exception:
            _MODEL = {}
    return _MODEL


def _features(gap_years, org_blank, company_type, program, role_missing):
    g = int(min(max(gap_years, 0), 25))
    d = {"gap": float(g)}
    for b in (1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20):
        d[f"gap_ge{b}"] = float(g >= b)
    d["org_blank"] = float(bool(org_blank))
    d["role_missing"] = float(bool(role_missing))
    ct = str(company_type or "").strip().lower()
    d["ct=" + (ct if ct in ("services", "product", "bfsi", "others") else "other")] = 1.0
    d["prog=" + _PROG.get(str(program or "").strip().lower(), "other")] = 1.0
    return d


def predict_band(gap_years, org_blank, company_type, program, role_missing) -> Optional[str]:
    """Returns EXP_0_1 / EXP_1_3 / EXP_3_5 / EXP_5_PLUS, or None if the model file is missing."""
    m = _load()
    if not m or gap_years is None:
        return None
    feats = _features(gap_years, org_blank, company_type, program, role_missing)
    scores = []
    for ci in range(len(m["classes"])):
        s = m["intercept"][ci]
        for name, v in feats.items():
            j = m["index"].get(name)
            if j is not None:
                s += m["coef"][ci][j] * v
        scores.append(s)
    best = max(range(len(scores)), key=lambda i: scores[i])
    return _BAND_KEY.get(m["classes"][best])

"""
Observed refund rate for the K most similar past learners of a program.

For a lead and a program, take a fixed number (K) of past learners from the refund funnel, nearest first:
  1. same persona and same experience band
  2. same persona, nearest experience bands
  3. similar personas (technical with technical, non-technical with non-technical), nearest experience first
  4. any learner of the program
Inside each step the newest cohorts come first. The result is a plain count ("6 of 40 requested a refund"), not a smoothed
estimate, together with how close the matched learners really are.
"""
import csv
import functools
import os
from typing import Any, Dict, List, Optional

K_MATCH = int(os.getenv("COHORT_MATCH_K", "40"))

LEARNER_OUTCOMES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "learner_outcomes.csv")

_EXP_ORDER = ["EXP_0_1", "EXP_1_3", "EXP_3_5", "EXP_5_PLUS"]
_TECH = {"SWE_BACKEND", "FRONTEND", "QA_SDET", "IT_SERVICES", "SYSTEMS_ENG", "DEVOPS_CLOUD", "DATA_ANALYST", "LEADERSHIP"}
# program codes used by the engine -> codes used in the outcomes file
_PROGRAM_FILE_CODE = {
    "P1_ACADEMY": "P1_ACADEMY", "P2_DSML": "P2_DSML", "P3_FDE": "P3_FDE",
    "P4_AIML_AGENTIC": "P4_AIML", "P4_AIML": "P4_AIML", "P5_DEVOPS_CLOUD": "P5_DEVOPS", "P5_DEVOPS": "P5_DEVOPS",
}


@functools.lru_cache(maxsize=1)
def _load() -> Dict[str, List[Dict[str, Any]]]:
    by_program: Dict[str, List[Dict[str, Any]]] = {}
    if not os.path.exists(LEARNER_OUTCOMES_PATH):
        return by_program
    with open(LEARNER_OUTCOMES_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["exp"] not in _EXP_ORDER:
                continue
            by_program.setdefault(row["program"], []).append({
                "persona": row["persona"], "exp": _EXP_ORDER.index(row["exp"]),
                "refunded": int(row["refunded"]), "cohort": row["cohort_month"],
            })
    # newest cohorts first, stable, so the choice is deterministic
    for rows in by_program.values():
        rows.sort(key=lambda r: r["cohort"], reverse=True)
    return by_program


def available() -> bool:
    return bool(_load())


def match_cohort(program_code: str, persona_key: str, exp_key: str, k: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """K nearest past learners of the program, or None when no outcomes file is available."""
    k = k or K_MATCH
    rows = _load().get(_PROGRAM_FILE_CODE.get(program_code, program_code))
    if not rows:
        return None
    e = _EXP_ORDER.index(exp_key) if exp_key in _EXP_ORDER else 1
    tech = persona_key in _TECH
    any_persona = persona_key is None            # persona unknown: do not guess it, use every learner of the program

    def tier(r) -> int:
        if any_persona:
            return 1 if r["exp"] == e else 2
        if r["persona"] == persona_key:
            return 1 if r["exp"] == e else 2
        if (r["persona"] in _TECH) == tech:
            return 3
        return 4

    # rows are already newest-first; a stable sort by (tier, experience distance) keeps recency inside each step
    ranked = sorted(rows, key=lambda r: (tier(r), abs(r["exp"] - e)))
    chosen = ranked[:k]
    n = len(chosen)
    refunds = sum(r["refunded"] for r in chosen)
    exact_rows = [r for r in rows if (any_persona or r["persona"] == persona_key) and r["exp"] == e]      # all exact matches, newest or not
    exact = len(exact_rows)
    exact_refunds = sum(r["refunded"] for r in exact_rows)
    same_persona = sum(1 for r in chosen if r["persona"] == persona_key)
    exact_used = sum(1 for r in chosen if tier(r) == 1)
    if any_persona:
        basis = "all personas, same experience band" if exact_used == n else "all personas, nearest experience bands"
    elif exact_used == n:
        basis = "same persona and experience band"
    elif same_persona == n:
        basis = "same persona, nearest experience bands"
    elif same_persona > 0:
        basis = "same persona first, widened to similar personas"
    else:
        basis = "similar personas (no learners with this persona in the program)"
    months = sorted({r["cohort"] for r in chosen})
    return {
        "n": n, "refunds": refunds,
        "refund_rate": round(100.0 * refunds / n, 1), "retention_rate": round(100.0 * (n - refunds) / n, 1),
        "exact_available": exact, "exact_refunds": exact_refunds, "exact_used": exact_used, "same_persona_used": same_persona,
        "basis": basis, "newest_cohort": months[-1], "oldest_cohort": months[0], "k": k,
    }

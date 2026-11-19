"""
Build the live tool-review workbook for a set of refund-funnel cohort months.

It pulls three things fresh every run, so the workbook always reflects the latest of each:
  1. the refund funnel (Raw sheet of the newest workbook in Database/): who bought what, who refunded
  2. the lead record of each learner from Metabase (needs the METABASE_* variables, nothing is stored in the file)
  3. the tool itself: primary and fallback program with confidence, from the current code and model

The workbook's analysis sheets are Excel formulas over the 'Learner Review' sheet and the 'Program Rates' sheet, so editing
a cell there (or a program rate) recalculates the analysis straight away. To refresh the data itself, run this script again.

    python tools/build_review_workbook.py                          # the last 3 mature cohort months
    python tools/build_review_workbook.py --months 2026-08,2026-09,2026-10
    python tools/build_review_workbook.py --cache Database/_review_leads.pkl    # reuse downloaded leads (skips Metabase)
"""
import argparse
import json
import os
import pickle
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

PROGRAMS = {"academy": "Program 1", "dsml": "Program 2", "fde": "Program 3", "aiml": "Program 4", "devops": "Program 5"}
TEAMS = {"Academy": "Academy team", "Data_Science": "Data Science team", "ai_ml": "AI/ML team", "fde": "FDE team", "DevOps": "DevOps team"}
EXP = {"EXP_0_1": "0 to 1 year", "EXP_1_3": "1 to 3 years", "EXP_3_5": "3 to 5 years", "EXP_5_PLUS": "5+ years"}
MAX_ROW = 10000
NAVY, GREY = "1F2A44", "F2F4F7"
HF = Font(bold=True, color="FFFFFF", size=10)
HFILL = PatternFill("solid", fgColor=NAVY)
THIN = Side(style="thin", color="D0D5DD")
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)


def newest_workbook():
    for n in ("Refunds Funnel (2).xlsx", "Refunds Funnel (1).xlsx"):
        p = os.path.join(ROOT, "Database", n)
        if os.path.exists(p):
            return p
    raise SystemExit("No refund funnel workbook found in Database/.")


# --------------------------------------------------------------------------------------------- data
def load_funnel(path):
    R = pd.read_excel(path, sheet_name="Raw").drop_duplicates("User Id").copy()
    R["email"] = R["Email"].astype(str).str.strip().str.lower()
    R["lead_email"] = R["Lead Email"].astype(str).str.strip().str.lower()
    R["refunded"] = (R["Refunded"].astype(str).str.strip().str.lower() == "true").astype(int)      # the funnel's own Refunded column
    cm = pd.to_datetime(R["Refunds Oms Cohort"], errors="coerce")
    R["month"] = cm.dt.strftime("%Y-%m")
    R["mature"] = (cm < cm.max()).astype(int)
    R["program"] = R["Intake Program"].astype(str).str.strip().str.lower().map(PROGRAMS)
    return R


def program_rates(R, first_month):
    """Refund rate per program from cohorts before the review window (so the review is not judged on its own data).
    A program with too little earlier history (for example one launched inside the window) uses every mature cohort."""
    early = R[(R.month < first_month) & (R.mature == 1) & R.program.notna()]
    allm = R[(R.mature == 1) & R.program.notna()]
    out = []
    for p in sorted(PROGRAMS.values()):
        e, a = early[early.program == p], allm[allm.program == p]
        if len(e) >= 200:
            out.append((p, round(float(e.refunded.mean()), 4), len(e), "Cohorts before " + first_month))
        else:
            out.append((p, round(float(a.refunded.mean()), 4), len(a), "All mature cohorts (too little earlier history)"))
    return out


def fetch_leads(emails, cache):
    if cache and os.path.exists(cache):
        print("using cached leads:", cache)
        return pd.read_pickle(cache)
    from src.arrival_view import fetch_arrival_leads              # the lead as seen on arrival, not the record created at the sale
    L = fetch_arrival_leads(emails)
    L["email"] = L["email"].astype(str).str.lower()
    L = L.drop_duplicates("email")
    if cache:
        L.to_pickle(cache)
    return L


def build_rows(R, L):
    from src.batch_processor import process_leads_dataframe
    L = L.drop_duplicates("email").set_index("email", drop=False)
    # learner email first; if not in Metabase, the Lead Email recorded in the refund funnel
    use = {}
    for r in R.itertuples():
        if r.email in L.index:
            use[r.email] = (r.email, "Email")
        elif r.lead_email in L.index and r.lead_email != "nan":
            use[r.email] = (r.lead_email, "Lead Email column")
    leads = L.loc[sorted({v[0] for v in use.values()})].reset_index(drop=True)
    res = {}
    for i in range(0, len(leads), 300):
        out, _ = process_leads_dataframe(leads.iloc[i:i + 300].reset_index(drop=True), include_export_df=False, index_offset=i)
        for x in out:
            res[str(x["person"]["email"]).lower()] = x
    rows = []
    for r in R.itertuples():
        lead_key, how = use.get(r.email, (None, "Not found"))
        x = res.get(lead_key) if lead_key else None
        pe = x["person"] if x else {}
        team = None
        if lead_key and "which_bda_team" in L.columns:
            t = str(L.loc[lead_key, "which_bda_team"] or "")
            teams = [s.strip() for s in t.split("/") if s.strip()]
            team = TEAMS.get(teams[0]) if teams else None
            ngroup = "One team" if len(teams) <= 1 else ("Two teams" if len(teams) == 2 else "Three or more teams")
        else:
            ngroup = None
        yn = lambda b: "Yes" if b else "No"
        org = str(pe.get("previous_org") or "").strip().lower()
        rows.append({
            "month": "Cohort " + r.month, "uid": None,
            "email": r.email, "bought": r.program, "mentee": None,
            "refunded_txt": "Yes" if r.refunded else "No",
            "prim": x["primary"].get("catalog_code") if x else None, "conf_p": x["primary"].get("confidence_score") if x else None,
            "fall": x["fallback"].get("catalog_code") if x else None, "conf_f": x["fallback"].get("confidence_score") if x else None,
            "also": ((x.get("also_consider") or {}).get("catalog_code")) if x else None,
            "enq": (pe.get("inbound_cat") or None) if x else None, "stated": bool(pe.get("inbound_stated")) if x else None,
            "found": "Yes" if x else "No", "matched_by": how, "team": team, "teams": ngroup,
            "persona": pe.get("normalized_persona"), "exp": EXP.get(pe.get("normalized_experience")), "set": pe.get("set_status"),
            "role_given": yn(pe.get("role_provided")) if x else None, "role_rec": yn(pe.get("role_recognized")) if x else None,
            "ctype_given": yn(pe.get("company_type_provided")) if x else None,
            "emp_given": yn(org not in ("", "none", "nan", "not applicable", "independent / transitioning", "self employed", "freelancer")) if x else None,
            "exp_from": pe.get("experience_basis"), "persona_from": pe.get("persona_basis"),
        })
    df = pd.DataFrame(rows)
    df["uid"] = R["User Id"].values
    df["mentee"] = R["Mentee Status"].values
    return df


# --------------------------------------------------------------------------------------------- workbook
COLS = [  # key, header, width, is_formula
    ("month", "Cohort month", 14), ("uid", "User Id", 12), ("email", "Email", 34), ("bought", "Program bought", 14),
    ("mentee", "Mentee status", 13), ("refunded_txt", "Refunded (actual)", 12),
    ("prim", "Tool primary program", 14), ("conf_p", "Confidence in primary (%)", 12), ("fall", "Tool fallback program", 14), ("conf_f", "Confidence in fallback (%)", 12), ("also", "Also consider program", 14),
    ("match", "Program bought was", 15), ("outcome", "Recommended program refunded?", 28),
    ("found", "Lead found in Metabase", 12), ("matched_by", "Lead matched by", 16), ("team", "BDA team that owned the lead", 18), ("teams", "Teams that handled the lead", 20),
    ("persona", "Persona", 34), ("exp", "Experience band", 14), ("set", "Diagnostic SET", 18),
    ("role_given", "Role given", 10), ("role_rec", "Role recognised", 11), ("ctype_given", "Company type given", 12), ("emp_given", "Employer given", 11),
    ("exp_from", "Experience taken from", 22), ("persona_from", "Persona taken from", 14),
    ("ref", "Refunded (1/0)", 10), ("also_hit", "Bought the also-consider program (1/0)", 14), ("eval", "Evaluated (1/0)", 10), ("cband", "Confidence band", 14),
    ("rb", "Program refund rate: bought", 13), ("rp", "Program refund rate: tool primary", 14),
]
L_ = {k: get_column_letter(i + 1) for i, (k, _, _) in enumerate(COLS)}
FORMULA_COLS = {"match", "outcome", "ref", "eval", "cband", "rb", "rp", "also_hit"}


def formula(key, r):
    c = lambda k: f"{L_[k]}{r}"
    if key == "match":
        return f'=IF({c("found")}<>"Yes","No Metabase record",IF({c("bought")}={c("prim")},"Primary",IF({c("bought")}={c("fall")},"Fallback","Neither")))'
    if key == "outcome":
        return (f'=IF(OR({c("match")}="Primary",{c("match")}="Fallback"),IF({c("refunded_txt")}="Yes","Refunded","Not refunded"),'
                f'IF({c("match")}="Neither","n/a (a different program was sold)","n/a"))')
    if key == "ref":
        return f'=IF({c("refunded_txt")}="Yes",1,0)'
    if key == "also_hit":
        return f'=IF(AND({c("match")}="Neither",{c("also")}<>"",{c("also")}={c("bought")}),1,0)'
    if key == "eval":
        return f'=IF(OR({c("match")}="Primary",{c("match")}="Fallback",{c("match")}="Neither"),1,0)'
    if key == "cband":
        o = c("conf_p")
        return f'=IF({o}="","",IF({o}<60,"Below 60%",IF({o}<70,"60 to 69%",IF({o}<80,"70 to 79%","80% and above"))))'
    if key == "rb":
        return f'=IFERROR(VLOOKUP({c("bought")},ProgramRates,2,FALSE),"")'
    if key == "rp":
        return f'=IFERROR(VLOOKUP({c("prim")},ProgramRates,2,FALSE),{c("rb")})'


def name_ranges(wb, nrows):
    for k, _, _ in COLS:
        wb.defined_names[f"LR_{k}"] = DefinedName(f"LR_{k}", attr_text=f"'Learner Review'!${L_[k]}$2:${L_[k]}${MAX_ROW}")


def style_header(ws, r, heads, h=44):
    for j, x in enumerate(heads, 1):
        c = ws.cell(r, j, x)
        c.font, c.fill, c.border = HF, HFILL, BOX
        c.alignment = Alignment(horizontal="left" if j == 1 else "center", vertical="center", wrap_text=True)
    ws.row_dimensions[r].height = h


def put(ws, r, vals, fmts=None, bold=False, shade=False):
    for j, v in enumerate(vals, 1):
        c = ws.cell(r, j, v)
        c.border, c.font = BOX, Font(size=10, bold=bold)
        c.alignment = Alignment(horizontal="left" if j == 1 else "center", vertical="center", wrap_text=True)
        if fmts and fmts.get(j):
            c.number_format = fmts[j]
        if shade:
            c.fill = PatternFill("solid", fgColor=GREY)


def title(ws, t, sub):
    ws.sheet_view.showGridLines = False
    ws.cell(1, 1, t).font = Font(bold=True, size=15, color=NAVY)
    ws.cell(2, 1, sub).font = Font(italic=True, size=10, color="667085")


def note(ws, r, t, ncols=7, h=30):
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncols)
    c = ws.cell(r, 1, t)
    c.alignment, c.font = Alignment(wrap_text=True, vertical="top"), Font(size=10)
    ws.row_dimensions[r].height = h


PCT, PTS = "0.0%", "+0.0;-0.0;0.0"


def write_data(wb, df):
    ws = wb.create_sheet("Learner Review")
    ws.sheet_view.showGridLines = False
    for j, (k, h, w) in enumerate(COLS, 1):
        c = ws.cell(1, j, h)
        c.font, c.fill, c.border = HF, HFILL, BOX
        c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[1].height = 44
    for i, rec in enumerate(df.to_dict("records"), 2):
        for j, (k, _, _) in enumerate(COLS, 1):
            v = formula(k, i) if k in FORMULA_COLS else rec.get(k)
            if isinstance(v, float) and pd.isna(v):
                v = None
            c = ws.cell(i, j, v)
            c.font, c.border = Font(size=10), BOX
            c.alignment = Alignment(vertical="center", horizontal="left" if k in ("email", "persona") else "center")
            if k in ("rb", "rp"):
                c.number_format = PCT
    ws.freeze_panes = "D2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLS))}{len(df) + 1}"
    return ws


def write_rates(wb, rates, months):
    ws = wb.create_sheet("Program Rates")
    title(ws, "Program refund rates used in the estimates", "Inputs. Change a rate and every sheet recalculates. Rebuilt from the refund funnel each time the script runs.")
    style_header(ws, 4, ["Program", "Refund rate", "Learners behind the rate", "Basis"], 30)
    for i, (p, rt, n, basis) in enumerate(rates, 5):
        put(ws, i, [p, rt, n, basis], {2: PCT}, shade=bool(i % 2))
    ws.column_dimensions["A"].width = 18; ws.column_dimensions["B"].width = 14; ws.column_dimensions["C"].width = 22; ws.column_dimensions["D"].width = 48
    wb.defined_names["ProgramRates"] = DefinedName("ProgramRates", attr_text=f"'Program Rates'!$A$5:$B${4 + len(rates)}")


def seg_formulas(dim, r):
    a = f"$A{r}"
    crit = f"LR_{dim},{a}" if dim else None
    base = "LR_eval,1" + (f",{crit}" if crit else "")
    n = f"COUNTIFS({base})"
    prim_n = f"COUNTIFS({base},LR_match,\"Primary\")"
    return [
        f"={n}",
        f'=IF($B{r}<30,"-",SUMIFS(LR_ref,{base})/$B{r})',
        f'=IF({prim_n}<20,"-",SUMIFS(LR_ref,{base},LR_match,"Primary")/{prim_n})',
        f'=IF(OR($C{r}="-",$D{r}="-"),"-",($D{r}-$C{r})*100)',
        f'=IF($C{r}="-","-",$C{r}+AVERAGEIFS(LR_rp,{base})-AVERAGEIFS(LR_rb,{base}))',
        f'=IF($C{r}="-","-",($F{r}-$C{r})*100)',
    ]


def write_segments(wb, df, months):
    ws = wb.create_sheet("Sales vs Tool by Segment")
    title(ws, "Refund rate when sales sold, and refund rate if the tool's primary had been sold",
          "Live formulas over the Learner Review sheet: " + ", ".join(months) + ", the five programs only, learners the tool evaluated.")
    ws.column_dimensions["A"].width = 44
    for c in "BCDEFG":
        ws.column_dimensions[c].width = 19
    ev = df[df.found == "Yes"]
    def labels(col, order=None):
        v = ev[col].dropna().astype(str)
        vc = v.value_counts()
        return [x for x in (order or list(vc.index)) if x in vc.index]
    secs = [("Overall", None, ["All learners"]),
            ("Cohort month", "month", sorted(df.month.unique())),
            ("Program bought", "bought", labels("bought", sorted(PROGRAMS.values()))),
            ("BDA team that owned the lead", "team", labels("team", list(TEAMS.values()))),
            ("How many teams handled the lead", "teams", labels("teams", ["One team", "Two teams", "Three or more teams"])),
            ("Persona", "persona", labels("persona")),
            ("Experience band", "exp", labels("exp", list(EXP.values()))),
            ("Diagnostic SET", "set", labels("set", ["SET Passed", "SET Attempted", "SET Not Attempted"])),
            ("Confidence in the tool's primary", "cband", ["Below 60%", "60 to 69%", "70 to 79%", "80% and above"])]
    heads = ["", "Learners", "Refund rate: sales as sold", "If tool's primary sold (observed basis)", "Change (points)", "If tool's primary sold (program-rate basis)", "Change (points)"]
    r = 4
    for name, dim, labs in secs:
        ws.cell(r, 1, name).font = Font(bold=True, size=12, color=NAVY); r += 1
        style_header(ws, r, heads, 48); r += 1
        for k, lab in enumerate(labs):
            put(ws, r, [lab] + seg_formulas(dim, r), {3: PCT, 4: PCT, 5: PTS, 6: PCT, 7: PTS}, bold=(dim is None), shade=bool(k % 2)); r += 1
        r += 1


def write_accuracy(wb, df, months):
    ws = wb.create_sheet("Recommendation Accuracy")
    title(ws, "How often the tool's recommendation was right, and what happened to those learners",
          "Live formulas. Right = the learner bought the tool's primary or fallback program. " + ", ".join(months) + ", the five programs only. "
          "The model was trained on these months, so these figures are higher than new leads will get: see the Held-Out Accuracy sheet.")
    ws.column_dimensions["A"].width = 46
    for c in "BCDEFGHI":
        ws.column_dimensions[c].width = 17
    H1 = ["Program bought was", "Learners", "Share of all learners", "Refunded", "Refunded %", "Not refunded", "Not refunded %"]
    ws.cell(4, 1, "1. Recommendation correct or not, and refund outcome").font = Font(bold=True, size=12, color=NAVY)
    style_header(ws, 5, H1, 34)
    N = "COUNTIFS(LR_eval,1)"
    def row1(r, lab, ncount, nref, bold=False, shade=False):
        put(ws, r, [lab, f"={ncount}", f"=B{r}/{N}", f"={nref}", f"=IF(B{r}=0,\"-\",D{r}/B{r})", f"=B{r}-D{r}", f"=IF(B{r}=0,\"-\",F{r}/B{r})"], {3: PCT, 5: PCT, 7: PCT}, bold=bold, shade=shade)
    row1(6, "Tool's primary", 'COUNTIFS(LR_match,"Primary")', 'SUMIFS(LR_ref,LR_match,"Primary")')
    row1(7, "Tool's fallback", 'COUNTIFS(LR_match,"Fallback")', 'SUMIFS(LR_ref,LR_match,"Fallback")', shade=True)
    row1(8, "Primary or fallback (recommendation correct)", 'COUNTIFS(LR_match,"Primary")+COUNTIFS(LR_match,"Fallback")', 'SUMIFS(LR_ref,LR_match,"Primary")+SUMIFS(LR_ref,LR_match,"Fallback")', bold=True)
    row1(9, "Neither (recommendation not matched)", 'COUNTIFS(LR_match,"Neither")', 'SUMIFS(LR_ref,LR_match,"Neither")', shade=True)
    row1(10, "All evaluated learners", N, "SUMIFS(LR_ref,LR_eval,1)")
    row1(11, "Neither, but bought the 'also consider' program", 'COUNTIFS(LR_also_hit,1)', 'SUMIFS(LR_ref,LR_also_hit,1)', shade=True)
    row1(12, "Covered including 'also consider'", 'COUNTIFS(LR_match,"Primary")+COUNTIFS(LR_match,"Fallback")+COUNTIFS(LR_also_hit,1)', 'SUMIFS(LR_ref,LR_match,"Primary")+SUMIFS(LR_ref,LR_match,"Fallback")+SUMIFS(LR_ref,LR_also_hit,1)', bold=True)
    def block(r, head, dim, labs):
        ws.cell(r, 1, head).font = Font(bold=True, size=12, color=NAVY)
        style_header(ws, r + 1, ["", "Learners", "Primary bought", "Fallback bought", "Primary or fallback bought", "Refunded % (of those)", "Not refunded % (of those)"], 40)
        for k, lab in enumerate(labs):
            q = r + 2 + k
            d = f"LR_{dim},$A{q}"
            pn, fn = f'COUNTIFS(LR_eval,1,{d},LR_match,"Primary")', f'COUNTIFS(LR_eval,1,{d},LR_match,"Fallback")'
            pr, fr = f'SUMIFS(LR_ref,LR_eval,1,{d},LR_match,"Primary")', f'SUMIFS(LR_ref,LR_eval,1,{d},LR_match,"Fallback")'
            put(ws, q, [lab, f"=COUNTIFS(LR_eval,1,{d})", f"=IF(B{q}=0,\"-\",{pn}/B{q})", f"=IF(B{q}=0,\"-\",{fn}/B{q})", f"=IF(B{q}=0,\"-\",({pn}+{fn})/B{q})",
                         f"=IF({pn}+{fn}=0,\"-\",({pr}+{fr})/({pn}+{fn}))", f"=IF({pn}+{fn}=0,\"-\",1-F{q})"], {3: PCT, 4: PCT, 5: PCT, 6: PCT, 7: PCT}, shade=bool(k % 2))
        return r + 2 + len(labs) + 1
    r = block(14, "2. By cohort month", "month", sorted(df.month.unique()))
    r = block(r, "3. By program bought", "bought", sorted(PROGRAMS.values()))
    # pairs
    ws.cell(r, 1, "4. If the primary was sold, would selling the fallback instead have lowered refunds?").font = Font(bold=True, size=12, color=NAVY)
    style_header(ws, r + 1, ["Recommended pair", "Bought the primary", "Refunded %", "Bought the fallback", "Refunded %", "Primary program rate", "Fallback program rate", "Primary", "Fallback"], 40)
    ev = df[df.found == "Yes"].copy()
    ev["m"] = ev.apply(lambda x: "Primary" if x.bought == x.prim else ("Fallback" if x.bought == x.fall else "Neither"), axis=1)
    pairs = []
    for (p, f), d in ev.groupby(["prim", "fall"]):
        if p in PROGRAMS.values() and f in PROGRAMS.values() and (d.m == "Primary").sum() >= 20 and (d.m == "Fallback").sum() >= 20:
            pairs.append((p, f, len(d)))
    pairs.sort(key=lambda x: -x[2])
    for k, (p, f, _) in enumerate(pairs):
        q = r + 2 + k
        c = f"LR_prim,$H{q},LR_fall,$I{q}"
        put(ws, q, [f"{p} primary, {f} fallback", f'=COUNTIFS({c},LR_match,"Primary")', f'=IFERROR(SUMIFS(LR_ref,{c},LR_match,"Primary")/B{q},"-")',
                    f'=COUNTIFS({c},LR_match,"Fallback")', f'=IFERROR(SUMIFS(LR_ref,{c},LR_match,"Fallback")/D{q},"-")',
                    f"=VLOOKUP($H{q},ProgramRates,2,FALSE)", f"=VLOOKUP($I{q},ProgramRates,2,FALSE)", p, f], {3: PCT, 5: PCT, 6: PCT, 7: PCT}, shade=bool(k % 2))
    q = r + 2 + len(pairs)
    if pairs:
        a, b = f"B{r + 2}:B{q - 1}", f"D{r + 2}:D{q - 1}"
        put(ws, q, ["All pairs above", f"=SUM({a})", f"=SUMPRODUCT({a},C{r + 2}:C{q - 1})/SUM({a})", f"=SUM({b})", f"=SUMPRODUCT({b},E{r + 2}:E{q - 1})/SUM({b})", "", "", "", ""], {3: PCT, 5: PCT}, bold=True)
    ws.freeze_panes = "B4"


def write_heldout(wb, path=None):
    """Accuracy on months the model had never seen (Database/honest_backtest.json, made by tools/honest_backtest.py)."""
    path = path or os.path.join(ROOT, "Database", "honest_backtest.json")
    if not os.path.exists(path):
        return
    import json
    res = json.load(open(path)).get("results", [])
    if not res:
        return
    ws = wb.create_sheet("Held-Out Accuracy")
    title(ws, "How the tool does on months it has never seen",
          "Each model was trained only on the cohorts before the cut-off, then run on the later months. This is what a new lead will get. Values come from tools/honest_backtest.py.")
    ws.column_dimensions["A"].width = 26
    for c in "BCDEFGHIJK":
        ws.column_dimensions[c].width = 16
    heads = ["Model trained on cohorts before", "Tested on", "Learners", "Bought the Recommended", "Bought the Fallback", "Bought the third row", "Bought a program not shown",
             "Recommended right %", "Recommended or Fallback right %", "Including the third row %"]
    style_header(ws, 4, heads, 58)
    for i, r in enumerate(res):
        row = 5 + i
        put(ws, row, [r["trained_before"], f"{r['tested_on'][0]} to {r['tested_on'][-1]}", r["learners"], r["primary"], r["fallback"], r["also"], r["none"],
                      f"=D{row}/C{row}", f"=(D{row}+E{row})/C{row}", f"=(D{row}+E{row}+F{row})/C{row}"], {8: PCT, 9: PCT, 10: PCT})
    last = 5 + len(res)
    if all("refunded" in r for r in res):
        r0 = last + 3
        ws.cell(r0 - 1, 1, "Refunds in the same test: the tool's picks against what sales sold").font = Font(bold=True, size=12, color=NAVY)
        style_header(ws, r0, ["Model trained on cohorts before", "Tested on", "Learners", "Refunded (all learners)", "Refund rate (all learners)", "Refund rate when the Recommended was bought",
                              "Refund rate when the Fallback was bought", "Expected refunds if the tool's Recommended had been sold", "Expected refunds for what sales sold", "Refunds avoided (negative = more refunds)"], 70)
        for i, r in enumerate(res):
            row, src = r0 + 1 + i, 5 + i
            put(ws, row, [r["trained_before"], f"{r['tested_on'][0]} to {r['tested_on'][-1]}", f"=C{src}", r["refunded"], f"=D{row}/C{row}",
                          f"=IF(D{src}=0,\"-\",{r['refunded_primary']}/D{src})", f"=IF(E{src}=0,\"-\",{r['refunded_fallback']}/E{src})",
                          r["expected_refunds_if_tool_primary_sold"], r["expected_refunds_for_what_sales_sold"], f"=I{row}-H{row}"],
                {5: PCT, 6: PCT, 7: PCT, 8: "0.0", 9: "0.0", 10: "+0.0;-0.0;0.0"})
        last = r0 + len(res)
        note(ws, last + 1, "Expected refunds use each program's refund rate from the cohorts before the test months, so the comparison is not judged on its own data. "
             "Across these tests the tool's Recommended program does not reliably lower refunds: it avoids refunds in some tests and adds them in others.", 10, 44)
        last += 1
    note(ws, last + 2, "HONEST STATEMENT: the tool shows the programs a lead is likely to take, with the refund record of each program beside them. "
         "It does not yet show that following its recommendation lowers refunds. Which program is sold moves the refund rate only a little (program rates run from about 17% to 25%).", 10, 48)
    note(ws, last + 1, "Read this sheet, not the Recommendation Accuracy sheet, as the accuracy to expect on new leads. The other sheet marks learners the model was trained on, so it looks better. "
         "FDE launched in September, so a model trained before September has never seen an FDE buyer and cannot recommend it.", 10, 48)


def write_coverage(wb, df, months):
    ws = wb.create_sheet("Lead Data Coverage")
    title(ws, "How much lead data comes back from Metabase", "Live formulas over the Learner Review sheet. " + ", ".join(months) + ", the five programs only.")
    ws.column_dimensions["A"].width = 54; ws.column_dimensions["B"].width = 18; ws.column_dimensions["C"].width = 18
    style_header(ws, 4, ["Lead records", "Learners", "Share"], 30)
    put(ws, 5, ["Learners who bought one of the five programs", "=COUNTA(LR_email)", '=B5/B5'], {3: PCT})
    put(ws, 6, ["  Found by the learner's own email", '=COUNTIFS(LR_matched_by,"Email")', "=B6/$B$5"], {3: PCT}, shade=True)
    put(ws, 7, ["  Found only by the Lead Email column of the refund funnel", '=COUNTIFS(LR_matched_by,"Lead Email column")', "=B7/$B$5"], {3: PCT})
    put(ws, 8, ["Lead record found in Metabase", '=COUNTIFS(LR_found,"Yes")', "=B8/$B$5"], {3: PCT}, bold=True)
    put(ws, 9, ["No lead record in Metabase", '=COUNTIFS(LR_found,"No")', "=B9/$B$5"], {3: PCT}, shade=True)
    r = 10
    for m in sorted(df.month.unique()):
        put(ws, r, [m, f'=COUNTIFS(LR_month,$A{r},LR_found,"Yes")', f'=B{r}/COUNTIFS(LR_month,$A{r})'], {3: PCT}, shade=bool(r % 2)); r += 1
    r += 1
    ws.cell(r, 1, "Fields in the lead records found").font = Font(bold=True, size=12, color=NAVY); r += 1
    style_header(ws, r, ["Field", "Records", "Share of records found"], 30); r += 1
    fields = [("Role filled in", 'COUNTIFS(LR_found,"Yes",LR_role_given,"Yes")'), ("Role recognised by the tool", 'COUNTIFS(LR_found,"Yes",LR_role_rec,"Yes")'),
              ("Company type filled in", 'COUNTIFS(LR_found,"Yes",LR_ctype_given,"Yes")'), ("Employer name filled in (not blank, self-employed or freelancer)", 'COUNTIFS(LR_found,"Yes",LR_emp_given,"Yes")'),
              ("Experience from stated years", 'COUNTIFS(LR_found,"Yes",LR_exp_from,"stated*")'), ("Experience worked out from organisation start year", 'COUNTIFS(LR_found,"Yes",LR_exp_from,"organisation*")'),
              ("Persona worked out from the role", 'COUNTIFS(LR_found,"Yes",LR_persona_from,"role")'), ("Persona inferred (role missing or unclear)", 'COUNTIFS(LR_found,"Yes",LR_persona_from,"inferred")'),
              ("Persona unknown", 'COUNTIFS(LR_found,"Yes",LR_persona_from,"unknown")')]
    for k, (lab, f) in enumerate(fields):
        put(ws, r, [lab, "=" + f, f"=B{r}/$B$8"], {3: PCT}, shade=bool(k % 2)); r += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook", default=None, help="refund funnel workbook (default: newest in Database/)")
    ap.add_argument("--months", default=None, help="comma list of cohort months YYYY-MM (default: the last 3 mature months)")
    ap.add_argument("--cache", default=None, help="pickle file for the downloaded Metabase leads; reused if it exists")
    ap.add_argument("--out", default=os.path.join(ROOT, "Database", "Refund Funnel Tool Review (Live).xlsx"))
    ap.add_argument("--backtest", default=None, help="honest backtest JSON for the Held-Out Accuracy sheet (default: Database/honest_backtest.json)")
    a = ap.parse_args()
    src = a.workbook or newest_workbook()
    R = load_funnel(src)
    mature = sorted(R.loc[R.mature == 1, "month"].dropna().unique())
    months = a.months.split(",") if a.months else mature[-3:]
    W = R[R.month.isin(months) & R.program.notna()].copy()
    print(f"{len(W)} learners in {months} who bought one of the five programs")
    emails = sorted({e for e in list(W.email) + [x for x in W.lead_email if x != "nan"]})
    L = fetch_leads(emails, a.cache)
    df = build_rows(W, L)
    # Learners the tool identifies as students or fresh graduates are left out: they are sent to the prerequisite gate, not matched to a program.
    students = df.persona.astype(str).str.startswith(("Student", "Postgraduate"))
    print(f"leaving out {int(students.sum())} identified students")
    df = df[~students].reset_index(drop=True)
    rates = program_rates(R, months[0])
    wb = Workbook(); wb.remove(wb.active)
    df_labels = df.copy()
    write_accuracy(wb, df_labels, ["Cohort " + m for m in months])
    write_heldout(wb, a.backtest)
    write_segments(wb, df_labels, ["Cohort " + m for m in months])
    write_coverage(wb, df_labels, ["Cohort " + m for m in months])
    write_data(wb, df)
    write_rates(wb, rates, months)
    name_ranges(wb, len(df))
    wb.calculation.fullCalcOnLoad = True
    wb.save(a.out)
    print("saved", a.out, len(df), "rows")


if __name__ == "__main__":
    main()

"""
Role -> persona mapping.

Every persona key is one of: NON_TECH, QA_SDET, DATA_ANALYST, DEVOPS_CLOUD, SYSTEMS_ENG, LEADERSHIP, FRONTEND, IT_SERVICES, SWE_BACKEND.

How a role is read, in this order:
  1. Placeholder or empty text ("NA", "Other", "-", blank) says nothing about the person: result is None (unknown).
  2. Exact CRM role values (the dropdown values that cover most leads) map directly. Where the dropdown value is ambiguous in the
     learner data ("Manager", "AI Engineer"), the result is None so the other fields decide.
  3. Keyword rules on whole words, checked tech first (so "Healthcare Software Engineer" is a software engineer) and then non-tech.
  4. Anything left is unknown (None). The caller decides what to do with unknown (company type, program interest) and must not
     silently treat it as non-technical.

Checked against the personas learners and sales reported in the refund funnel: on roles it can map, it agrees on technical vs non-technical for about 86% of 4,767 learners.
"""
import re
from typing import Optional, Tuple

PERSONAS = ("NON_TECH", "QA_SDET", "DATA_ANALYST", "DEVOPS_CLOUD", "SYSTEMS_ENG", "LEADERSHIP", "FRONTEND", "IT_SERVICES", "SWE_BACKEND")

PLACEHOLDERS = {
    "", "na", "n a", "n/a", "none", "nil", "no", "nan", "null", "other", "others", "26 others", "26_others", "-", ".", "..", "nothing",
    "not applicable", "not specified", "not available", "unknown", "general professional career switcher", "general tech professional",
    "prospective learner", "non", "not", "yes", "nill", "employee", "working", "working professional", "professional", "job", "service", "private job",
}

# Exact values (after normalising) -> persona. Data-checked against the personas learners reported.
EXACT = {
    # software
    "backend engineer": "SWE_BACKEND", "fullstack engineer": "SWE_BACKEND", "full stack engineer": "SWE_BACKEND", "software engineer": "SWE_BACKEND",
    "senior software engineer": "SWE_BACKEND", "software developer": "SWE_BACKEND", "senior software developer": "SWE_BACKEND",
    "associate software engineer": "SWE_BACKEND", "software engineer developer": "SWE_BACKEND", "lead software engineer": "SWE_BACKEND",
    "principal software engineer": "SWE_BACKEND", "senior engineer": "SWE_BACKEND", "programmer analyst": "SWE_BACKEND",
    "android engineer": "SWE_BACKEND", "ios engineer": "SWE_BACKEND", "mobile engineer": "SWE_BACKEND", "sde": "SWE_BACKEND", "swe": "SWE_BACKEND",
    "frontend engineer": "FRONTEND",
    # leadership
    "engineering leadership": "LEADERSHIP", "backend architect": "LEADERSHIP", "security leadership": "LEADERSHIP", "technology lead": "LEADERSHIP",
    "tech lead": "LEADERSHIP", "technical lead": "LEADERSHIP", "team lead": "LEADERSHIP", "program manager": "LEADERSHIP", "consultant": "LEADERSHIP",
    "senior consultant": "LEADERSHIP", "associate consultant": "LEADERSHIP", "technical consultant": "LEADERSHIP", "principal consultant": "LEADERSHIP",
    # data
    "data scientist": "DATA_ANALYST", "data analyst": "DATA_ANALYST", "data engineer": "DATA_ANALYST", "senior data engineer": "DATA_ANALYST",
    "research engineers": "DATA_ANALYST", "research engineer": "DATA_ANALYST", "product manager": "DATA_ANALYST",
    "associate": "DATA_ANALYST", "senior associate": "DATA_ANALYST", "analyst": "DATA_ANALYST", "business analyst": "DATA_ANALYST",
    # platform, quality, support
    "devops engineer": "DEVOPS_CLOUD", "release engineer": "DEVOPS_CLOUD", "cloud engineer": "DEVOPS_CLOUD", "sre": "DEVOPS_CLOUD",
    "sdet": "QA_SDET", "qa engineer": "QA_SDET", "test engineer": "QA_SDET", "tester": "QA_SDET",
    "support engineer": "IT_SERVICES", "database administrator": "IT_SERVICES", "dba": "IT_SERVICES", "system administrator": "DEVOPS_CLOUD",
    "system engineer": "SYSTEMS_ENG", "systems engineer": "SYSTEMS_ENG",
    # not technical
    "non coder": "NON_TECH", "non-coder": "NON_TECH", "student": "NON_TECH", "fresher": "NON_TECH", "college student": "NON_TECH",
    "engineering intern": "IT_SERVICES", "intern": "NON_TECH", "teacher": "NON_TECH", "assistant professor": "NON_TECH", "professor": "NON_TECH",
    "co founder": "NON_TECH", "cofounder": "NON_TECH", "founder": "NON_TECH", "owner": "NON_TECH", "freelancer": "NON_TECH", "self employed": "NON_TECH",
    "product designer": "NON_TECH", "designer": "NON_TECH", "hr": "NON_TECH", "sales": "NON_TECH", "accountant": "NON_TECH",
    "executive": "NON_TECH", "assistant manager": "NON_TECH", "senior manager": "NON_TECH", "avp": "NON_TECH", "vp": "NON_TECH", "vice president": "NON_TECH",
    "engineer": "NON_TECH",          # a plain "Engineer" is mostly a mechanical, civil or electrical engineer in the learner data
}
# Dropdown values whose meaning is not settled by the text alone: the other fields decide.
AMBIGUOUS_EXACT = {"manager", "ai engineer", "specialist", "officer", "lead", "head", "director"}


def normalize(text) -> str:
    t = str(text or "").lower().replace("\t", " ")
    t = t.replace("&", " and ")
    t = re.sub(r"[_\-/•|,()\\]+", " ", t)
    t = re.sub(r"[^a-z0-9+#. ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _has(t: str, words) -> bool:
    return any(re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", t) for w in words)


_STUDENT = ["not working", "no job", "house wife", "housewife", "home maker", "homemaker", "studying", "study", "research scholar", "student", "students", "fresher", "freshers", "intern", "trainee", "undergraduate", "undergrad", "learner", "non coder", "noncoder",
            "non tech", "nontech", "non technical", "career break", "career switcher", "sabbatical", "gap year", "homemaker", "housewife", "unemployed",
            "job seeker", "looking for job"]
_QA = ["qa", "sdet", "tester", "testing", "test engineer", "test automation", "automation tester", "quality assurance", "quality analyst", "manual testing", "manual tester"]
_DATA = ["data scientist", "data science", "data analyst", "data analytics", "data engineer", "data engineering", "analytics", "analyst", "business intelligence", "bi developer",
         "bi engineer", "power bi", "tableau", "machine learning", "ml engineer", "mle", "ai engineer", "ai ml", "aiml", "nlp", "computer vision", "deep learning", "applied scientist",
         "research scientist", "research engineer", "etl", "big data", "statistician", "data architect", "mlops", "llm", "generative ai", "genai", "decision scientist"]
_DEVOPS = ["devops", "sre", "site reliability", "cloud", "infrastructure", "kubernetes", "docker", "terraform", "platform engineer", "sysadmin", "system administrator",
           "systems administrator", "network engineer", "network administrator", "network architect", "security engineer", "cyber security", "cybersecurity", "infosec",
           "soc analyst", "penetration tester", "release engineer", "build and release", "aws engineer", "azure"]
_SYSTEMS = ["embedded", "firmware", "hardware", "vlsi", "iot", "kernel", "device driver", "fpga", "asic", "system engineer", "systems engineer", "systems architect"]
_LEAD = ["engineering manager", "tech lead", "technical lead", "technology lead", "software manager", "development manager", "architect", "cto", "chief technology officer",
         "vp engineering", "vp of engineering", "head of engineering", "director of engineering", "director engineering", "engineering leadership", "tech leadership",
         "principal engineer", "staff engineer", "lead engineer", "lead developer", "distinguished engineer", "program manager", "delivery manager", "technical manager", "it manager"]
_FRONT = ["frontend", "front end", "ui developer", "ui engineer", "web developer", "web engineer", "react", "angular", "vue", "javascript developer"]
_SWE = ["software", "developer", "programmer", "sde", "swe", "backend", "back end", "fullstack", "full stack", "application engineer", "application developer",
        "java", "python", "golang", ".net", "c++", "c#", "node", "django", "spring boot", "android", "ios", "mobile", "flutter", "ruby", "rust", "scala", "php", "coder", "technical analyst"]
_ITSERV = ["support", "maintenance", "helpdesk", "help desk", "service desk", "production support", "application support", "desktop support", "dba", "database administrator",
           "database engineer", "it services", "it analyst", "it executive", "consultant", "technical consultant", "rpa", "salesforce", "servicenow", "sap", "erp", "implementation engineer",
           "solutions engineer", "sales engineer", "pre sales", "presales", "post sales"]
_NONTECH = ["teaching", "trainer", "proprietor", "ceo", "self", "supervisor", "admin", "data entry", "process associate", "freelance", "project engineer", "design engineer", "vice president", "nurse", "doctor", "physician", "surgeon", "dentist", "pharmacist", "clinical", "hospital", "healthcare", "lawyer", "advocate", "legal", "paralegal", "teacher", "professor",
            "lecturer", "tutor", "instructor", "faculty", "principal", "librarian", "chef", "cook", "hotel", "hospitality", "restaurant", "driver", "pilot", "warehouse", "logistics",
            "supply chain", "cashier", "retail", "merchandiser", "customer service", "customer care", "call center", "bpo", "telecaller", "receptionist", "operations", "sales", "business development",
            "bde", "bda", "marketing", "seo", "social media", "content", "copywriter", "hr", "human resources", "recruiter", "talent acquisition", "payroll", "accountant", "accounts", "accounting", "auditor",
            "finance", "banking", "banker", "bank", "insurance", "underwriter", "actuary", "relationship manager", "mechanical", "civil", "chemical", "electrical", "electronics", "automobile",
            "production", "quality control", "designer", "ui ux", "ux", "graphic", "artist", "journalist", "farmer", "agriculture", "electrician", "plumber", "mechanic", "technician", "police",
            "army", "navy", "government", "civil servant", "clerk", "executive", "administrator", "secretary", "assistant", "founder", "co founder", "cofounder", "owner", "freelancer",
            "self employed", "business", "entrepreneur", "product manager", "project coordinator", "coordinator", "vp", "avp", "director", "manager"]


def classify_role(role) -> Tuple[Optional[str], str]:
    """Returns (persona_key or None, reason). None means the text does not settle it."""
    t = normalize(role)
    if t in PLACEHOLDERS:
        return None, "no usable role"
    if t in AMBIGUOUS_EXACT:
        return None, "ambiguous title"
    if t in EXACT:
        return EXACT[t], "known role"
    if re.fullmatch(r"(sde|swe|sdet)\s?[0-9ivx]+", t):
        return ("QA_SDET" if t.startswith("sdet") else "SWE_BACKEND"), "known role"
    if _has(t, ["intern", "interns", "internship", "trainee"]):
        rest = re.sub(r"\b(intern|interns|internship|trainee)\b", " ", t)
        for key, words in (("QA_SDET", _QA), ("DEVOPS_CLOUD", _DEVOPS), ("SYSTEMS_ENG", _SYSTEMS), ("DATA_ANALYST", _DATA), ("FRONTEND", _FRONT), ("SWE_BACKEND", _SWE)):
            if _has(rest, words):
                return key, "technical intern"
        if _has(rest, ["engineering", "engineer", "technical", "tech", "it"]):
            return "IT_SERVICES", "technical intern"
        return "NON_TECH", "intern in a non-technical field"
    if _has(t, _STUDENT):
        return "NON_TECH", "student, fresher or career break"
    # an "analyst" in finance, risk, operations and similar functions is not a data role
    if "analyst" in t and _has(t, ["financial", "finance", "credit", "risk", "investment", "equity", "marketing", "market", "hr", "operations", "process", "claims",
                                   "underwriting", "audit", "tax", "accounts", "legal", "compliance", "supply chain", "sales", "research"]) \
            and not _has(t, ["data", "business intelligence", "bi", "analytics", "python", "sql", "machine learning"]):
        return "NON_TECH", "non-technical analyst role"
    # technical, most specific first
    for key, words, why in (("QA_SDET", _QA, "testing role"), ("DEVOPS_CLOUD", _DEVOPS, "platform or infrastructure role"),
                            ("SYSTEMS_ENG", _SYSTEMS, "systems or embedded role"), ("DATA_ANALYST", _DATA, "data role"),
                            ("LEADERSHIP", _LEAD, "technical leadership role"), ("FRONTEND", _FRONT, "frontend role"),
                            ("SWE_BACKEND", _SWE, "software role"), ("IT_SERVICES", _ITSERV, "IT services or support role")):
        if _has(t, words):
            return key, why
    if _has(t, _NONTECH):
        return "NON_TECH", "non-technical role"
    return None, "unrecognised role"

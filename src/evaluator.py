import os
import json
import re
import datetime
from .matrix_engine import (
    get_cohort_stats, get_persona_level_stats, normalize_persona, normalize_experience, normalize_program,
    classify_world_domain, get_canonical_persona_name, match_token, match_any
)

from .market_intelligence import get_market_intelligence
from .cohort_matcher import match_cohort, available as cohort_available
from . import learned_recommender as learned

# ==============================================================================
# OFFICIAL SCALER 5-PROGRAM CATALOG DEFINITIONS (from Documentation_Scaler_Updated.pdf)
# ==============================================================================
# Program 1: Software & AI Engineering Program (Scaler Academy)
# Program 2: Modern Data Science & Machine Learning with Specialization in AI (DSML)
# Program 3: AI Forward Deployed Engineer (FDE) Program
# Program 4: AI & Machine Learning with Agentic AI Program
# Program 5: DevOps, Cloud & AI Platform Engineering Program
# ==============================================================================

def clean_str(val, default=""):
    if val is None or str(val).strip().lower() in ['nan', 'none', 'null', '']:
        return default
    return str(val).strip()

def get_track_duration(program_str, track_str):
    p_lower = str(program_str).lower()
    t_lower = str(track_str).lower()
    
    # Program 1: Scaler Academy (PDF Page 3)
    if 'academy' in p_lower or 'program 1' in p_lower:
        if 'beginner' in t_lower:
            return '12 - 18 Months'
        elif 'intermediate' in t_lower:
            return '12 Months'
        elif 'advanced' in t_lower:
            return '10 - 17 Months'
        return '12 Months'
        
    # Program 2: DSML (PDF Page 5)
    elif 'dsml' in p_lower or 'data science' in p_lower or 'program 2' in p_lower:
        if 'beginner' in t_lower:
            return '16 - 20 Months'
        elif 'intermediate' in t_lower or 'core' in t_lower or 'predictive' in t_lower or 'advanced' in t_lower:
            return '14 - 16 Months'
        return '14 - 16 Months'
        
    # Program 3: AI Forward Deployed Engineer (FDE) (PDF Page 8)
    elif 'fde' in p_lower or 'forward deployed' in p_lower or 'program 3' in p_lower:
        return '12 Months'
        
    # Program 4: AI & ML with Agentic AI (PDF Page 12)
    elif 'agentic' in p_lower or 'program 4' in p_lower or 'aiml' in p_lower:
        if 'beginner' in t_lower or 'foundation' in t_lower:
            return '12 - 15 Months'
        return '12 - 15 Months'
        
    # Program 5: DevOps, Cloud & AI Platform Engineering (PDF Page 16)
    elif 'devops' in p_lower or 'cloud' in p_lower or 'platform' in p_lower or 'program 5' in p_lower:
        return '14 - 18 Months'
        
    return '12 Months'

def classify_education(education_str):
    if not education_str:
        return 'GRAD_UNKNOWN'
    edu = str(education_str).lower().strip()
    if edu in ['nan', 'none', 'null', '', '-', 'unknown']:
        return 'GRAD_UNKNOWN'
    
    # 1. Recognized higher degrees or post-graduate qualifications
    is_pg_diploma = any(k in edu for k in ['pg diploma', 'post graduate diploma', 'pgdca', 'pgdbm', 'pgdm'])
    
    below_grad_patterns = [
        r'\b(1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th|11th|12th)\b',
        r'\b[1-9]\s*(st|nd|rd|th)?\s*(standard|std|class|grade|pass)\b',
        r'\b10\s*pass\b', r'\b12\s*pass\b',
        r'\bhsc\b', r'\bssc\b', r'\bintermediate\b', r'\binter\b',
        r'\b10\+2\b', r'\bmatric\b', r'\bmatriculation\b', r'\bpolytechnic\b',
        r'\bdiploma\b', r'\biti\b', r'\bbelow graduation\b', r'\bhigh school\b',
        r'\bmiddle school\b', r'\bprimary school\b', r'\bunder matric\b', r'\bnon[- ]matric\b',
        r'\bpuc\b', r'\bhigher secondary\b', r'\bschooling\b', r'\bsecondary school\b'
    ]

    has_explicit_degree = any(re.search(pat, edu) for pat in [
        r'\bb\.?\s*tech\b', r'\bbtech\b', r'\bb\.?\s*e\b', r'\bbca\b', r'\bmca\b',
        r'\bm\.?\s*tech\b', r'\bmtech\b', r'\bb\.?\s*sc\b', r'\bm\.?\s*sc\b',
        r'\bbachelor\b', r'\bmaster\b', r'\bphd\b', r'\bmba\b', r'\bbba\b',
        r'\bb\.?\s*com\b', r'\bb\.?\s*a\b', r'\bdegree\b', r'\bgraduated\b', r'\bgraduate\b'
    ])

    # Check for Below Graduation (10th, 12th, Polytechnic, Undergraduate Diploma)
    is_below_grad = any(re.search(pat, edu) for pat in below_grad_patterns)
    if is_below_grad and not is_pg_diploma and not has_explicit_degree:
        return 'BELOW_GRAD'

    # Check for CS degrees
    has_cs_degree = any(k in edu for k in [
        'b.tech cs', 'b.tech cse', 'b.tech it', 'be cs', 'be cse', 'be it',
        'bca', 'mca', 'm.tech cs', 'm.tech cse', 'm.tech it', 'computer science',
        'information tech', 'software eng'
    ])
    if has_cs_degree:
        return 'GRAD_CS'

    # Check for Non-CS degrees
    has_non_cs_degree = any(k in edu for k in [
        'b.com', 'b.a', 'bba', 'bhm', 'b.des', 'llb', 'mbbs', 'b.pharm',
        'mechanical', 'civil', 'chemical', 'electrical', 'biotech', 'arts',
        'commerce', 'humanities'
    ])
    if has_non_cs_degree and not any(k in edu for k in ['b.tech', 'b.e', 'btech', 'engineering']):
        return 'GRAD_NON_CS'

    return 'GRAD_GENERAL'

def parse_academic_credentials(email: str, education_str: str, org_str: str, org_year_str: str = ""):
    """
    Infers degree level (PG vs UG), entry batch year, and estimated graduation year
    from candidate email patterns, education string, and organization fields.
    """
    em = str(email or '').strip().lower()
    user_part = em.split('@')[0] if '@' in em else em
    edu_lower = str(education_str or '').lower()
    org_lower = str(org_str or '').lower()
    combined_text = f"{em} {edu_lower} {org_lower} {str(org_year_str or '')}"

    # 1. Detect Postgraduate (PG) status: M.Tech, MCA, MBA, M.Sc, MS, PhD
    pg_keywords = [
        'm.tech', 'mtech', 'mca', 'mba', 'm.sc', 'msc', 'master', 'post graduate',
        'postgraduate', 'phd', 'doctorate', 'm.e.', 'm.e ', 'me cse', 'ms in cs'
    ]
    # Email patterns indicating PG: e.g. '24m05', 'cs24m', 'h2024' (BITS higher degree)
    is_pg_email = bool(re.search(r'\b[a-z]{0,4}\d{2}m\d{2,}', user_part) or re.search(r'^h20\d{2}', user_part) or 'mtech' in user_part or 'mca' in user_part)
    is_pg = any(k in edu_lower for k in pg_keywords) or is_pg_email or ('pg' in user_part and ('student' in em or 'ac.in' in em)) or ('fms.edu' in em or 'iim' in em or 'xlri' in em or 'isb' in em)

    # 2. Extract Entry Batch Year or Explicit Graduation Year
    entry_year = None
    explicit_grad_year = None

    # Check if org_str is an academic institution (College / University / School)
    is_org_academic = any(k in str(org_str or '').lower() for k in [
        'college', 'university', 'campus', 'institute', 'iit', 'nit', 'iiit', 'bits', 'school',
        'academy', 'polytechnic', 'vidyapith', 'engineering college', 'technology institute'
    ])
    # If org_year_str is provided and org_str is academic, treat it as graduation / batch year
    # At a college or university the year given is the pass-out (graduation) year
    if org_year_str and is_org_academic and re.search(r'\b(19\d\d|20\d\d)\b', str(org_year_str)):
        explicit_grad_year = int(re.search(r'\b(19\d\d|20\d\d)\b', str(org_year_str)).group(1))

    # Extract 4-digit year from username (e.g. h2024, f2022, kavya.2023)
    m4_user = re.search(r'(19\d\d|20[12]\d)', user_part)
    # Extract 2-digit year prefix from roll number (e.g. 24m05, 22b03, cs23b, ee21b)
    m2_user = re.search(r'(?:^|[a-z]{1,4})([12]\d)(?:[a-z]{1,2}|\d{3,})', user_part)

    # Check combined text specifically within education string or user part
    four_digit_match = re.search(r'\b(19\d\d|20\d\d)\b', f"{edu_lower} {user_part}")

    if m4_user:
        yr = int(m4_user.group(1))
        entry_year = yr
    elif m2_user:
        yr_short = int(m2_user.group(1))
        if 15 <= yr_short <= 30:
            entry_year = 2000 + yr_short
    elif four_digit_match:
        yr = int(four_digit_match.group(1))
        if yr >= 2026:
            explicit_grad_year = yr
        else:
            entry_year = yr

    # 3. Calculate Estimated Graduation Year
    current_year = 2026
    expected_grad_year = explicit_grad_year

    if not expected_grad_year and entry_year:
        if is_pg:
            # Master's degrees are typically 2 years
            expected_grad_year = entry_year + 2
        elif any(k in edu_lower for k in ['bca', 'b.sc', 'bsc', 'b.com', 'bba', 'b.a']):
            # 3-year bachelor degrees
            expected_grad_year = entry_year + 3
        else:
            # 4-year engineering degrees (B.Tech / B.E default)
            expected_grad_year = entry_year + 4

    # 4. Strict Degree Eligibility Determination
    # Rule: Candidates MUST have completed graduation to be eligible for any Scaler course.
    # PG students are eligible because they ALREADY completed their Bachelor's degree.
    # UG college students who have not completed graduation (expected_grad_year >= 2026 or currently enrolled) are NOT eligible.
    degree_tier = "Postgraduate (Master's / PG)" if is_pg else "Undergraduate (Bachelor's / UG)"

    if is_pg:
        # Postgraduate students ALREADY hold an undergraduate bachelor degree
        is_eligible = True
        status_text = "Eligible (Master's Student - Degree Verified)"
        batch_label = f"Batch {expected_grad_year} (PG Master's)" if expected_grad_year else "Master's Degree Enrolled"
    elif expected_grad_year and expected_grad_year >= current_year:
        # Currently enrolled undergraduate student who has NOT graduated yet
        is_eligible = False
        status_text = f"Ineligible (College Student - Batch {expected_grad_year} Degree Incomplete)"
        batch_label = f"College Student (Batch {expected_grad_year} - Expected Grad)"
    elif expected_grad_year and expected_grad_year < current_year:
        # Graduated in past (e.g. 2025 or earlier)
        is_eligible = True
        status_text = f"Eligible (Graduated - Batch {expected_grad_year})"
        batch_label = f"Batch {expected_grad_year} (Passed Out)"
    else:
        is_eligible = True
        status_text = "Degree Verified"
        batch_label = "Graduated / Degree Holder"

    return {
        'is_pg': is_pg,
        'degree_tier': degree_tier,
        'entry_year': entry_year,
        'expected_grad_year': expected_grad_year,
        'is_eligible': is_eligible,
        'status_text': status_text,
        'batch_label': batch_label
    }

def calculate_confidence(program_name, inbound_cat, cohort_size, retention_rate, sat_status, sat_score, edu_level, inbound_stated=True, edu_assumed=False):
    """
    Computes an empirical 0-100 Confidence Score based on:
    1. Historical Cohort Sample Size (35%)
    2. Historical Retention Rate (25%)
    3. Inbound Intent Alignment (25%)
    4. Diagnostic SAT & Academic Aptitude (15%)
    """
    if edu_level == 'BELOW_GRAD':
        return {
            'score': 0,
            'tier': 'Low',
            'rationale': 'Ineligible: Candidate does not satisfy Bachelor degree prerequisite.',
            'breakdown': {
                'cohort_pts': 0, 'cohort_max': 35, 'cohort_desc': 'Ineligible',
                'ret_pts': 0, 'ret_max': 25, 'ret_desc': 'Ineligible',
                'intent_pts': 0, 'intent_max': 25, 'intent_desc': 'Ineligible',
                'apt_pts': 0, 'apt_max': 15, 'apt_desc': 'Degree prerequisite unfulfilled'
            }
        }
    
    # 1. Empirical Cohort Sample Size (35 pts)
    if cohort_size >= 100:
        cohort_pts = 35
        cohort_desc = f"Robust cohort backing (N={cohort_size})"
    elif cohort_size >= 30:
        cohort_pts = 28
        cohort_desc = f"Fair cohort backing (N={cohort_size})"
    elif cohort_size >= 10:
        cohort_pts = 18
        cohort_desc = f"Moderate cohort sample (N={cohort_size})"
    else:
        cohort_pts = 8
        cohort_desc = f"Small cohort sample (N={cohort_size})"

    # 2. Historical Retention Rate (25 pts)
    if retention_rate >= 80.0:
        ret_pts = 25
        ret_desc = f"high retention ({retention_rate}%)"
    elif retention_rate >= 75.0:
        ret_pts = 18
        ret_desc = f"moderate retention ({retention_rate}%)"
    else:
        ret_pts = 10
        ret_desc = f"elevated refund risk ({retention_rate}%)"

    # 3. Inbound Intent Alignment (25 pts)
    p_lower = str(program_name).lower()
    inbound_matched = (
        ('academy' in p_lower and inbound_cat == 'P1_ACADEMY') or
        ('dsml' in p_lower and inbound_cat == 'P2_DSML') or
        ('fde' in p_lower and inbound_cat == 'P3_FDE') or
        ('agentic' in p_lower and inbound_cat == 'P4_AIML_AGENTIC') or
        ('devops' in p_lower and inbound_cat == 'P5_DEVOPS_CLOUD')
    )
    inbound_synergistic = (
        ('academy' in p_lower and inbound_cat in ['P3_FDE', 'P5_DEVOPS_CLOUD']) or
        ('dsml' in p_lower and inbound_cat == 'P4_AIML_AGENTIC') or
        ('devops' in p_lower and inbound_cat == 'P1_ACADEMY')
    )

    if not inbound_stated:
        intent_pts = 10
        intent_desc = "no program interest stated by the lead"
    elif inbound_matched:
        intent_pts = 25
        intent_desc = "direct inbound intent match"
    elif inbound_synergistic:
        intent_pts = 20
        intent_desc = "lateral domain synergy"
    else:
        intent_pts = 10
        intent_desc = "curricular redirection"

    # 4. Diagnostic Assessment & Educational Foundation (15 pts)
    is_cs = edu_level == 'GRAD_CS'
    sat_status_clean = str(sat_status).lower()
    sat_cleared = 'passed' in sat_status_clean or ('score' in sat_status_clean and not any(k in sat_status_clean for k in ['pending', 'not']))
    
    if sat_cleared or (is_cs and not edu_assumed):
        apt_pts = 15
        apt_desc = "verified coding/academic foundations"
    elif ('attempted' in sat_status_clean and 'not' not in sat_status_clean) or (edu_level == 'GRAD_GENERAL' and not edu_assumed):
        apt_pts = 10
        apt_desc = "degree verified, SET pending"
    else:
        apt_pts = 5
        apt_desc = "diagnostic SET not yet attempted"

    total_score = cohort_pts + ret_pts + intent_pts + apt_pts
    total_score = min(100, max(0, total_score))

    if total_score >= 75:
        tier = 'High'
    elif total_score >= 55:
        tier = 'Mid'
    else:
        tier = 'Low'

    rationale = f"{tier} Confidence ({total_score}%): {cohort_desc}, {ret_desc}, {intent_desc}, and {apt_desc}."
    breakdown = {
        'cohort_pts': cohort_pts,
        'cohort_max': 35,
        'cohort_desc': cohort_desc,
        'ret_pts': ret_pts,
        'ret_max': 25,
        'ret_desc': ret_desc,
        'intent_pts': intent_pts,
        'intent_max': 25,
        'intent_desc': intent_desc,
        'apt_pts': apt_pts,
        'apt_max': 15,
        'apt_desc': apt_desc,
    }
    return {
        'score': total_score,
        'tier': tier,
        'rationale': rationale,
        'breakdown': breakdown
    }


def generate_role_pitch(raw_role, raw_exp, p_lower, t_lower, is_primary, persona=''):
    """
    Synthesizes a role-specific career pitch connecting the candidate's existing professional
    skills (e.g., accounting ledgers, clinical protocols, QA testing, sales funnels) to the target program track.
    """
    r_lower = str(raw_role).lower()
    p_lower = str(p_lower).lower()
    t_lower = str(t_lower).lower()

    # 0a. Security, Defense & Protective Services (Guard, Police, Military, etc.)
    if match_any(r_lower, ['security guard', 'guard', 'watchman', 'chowkidar', 'bouncer', 'police', 'military', 'army', 'navy', 'air force', 'firefighter', 'defense', 'defence', 'constable', 'inspector']):
        if 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your high vigilance, incident logging, and risk monitoring translate directly into "
                "structured data reporting, threat intelligence metrics, and predictive analytics from ground zero."
            )
        elif 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your background in physical security, perimeter protection, and rigorous protocol execution "
                "provides an intuitive transition into access management, system compliance, and cloud infrastructure monitoring."
            )
        else:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this Beginner Track starts from absolute ground zero (syntax, logic, loops). "
                "Your operational discipline and protocol compliance provide the consistency needed to build strong programming fundamentals without feeling overwhelmed."
            )

    # 0b. Hospitality, Facility & Cleaning Services (Sweeper, Cleaner, Janitor, Chef, Hotel Staff)
    if match_any(r_lower, ['sweeper', 'cleaner', 'janitor', 'housekeep', 'sanitation', 'maid', 'chef', 'cook', 'baker', 'waiter', 'server', 'steward', 'hotel', 'hospitality']):
        if 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this Beginner Track assumes zero prior technical knowledge. "
                "It starts with Excel formulas and visual dashboarding before introducing Python, allowing you to transition into data reporting step-by-step."
            )
        else:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this Beginner Track is engineered specifically for career pivoters with zero coding background. "
                "It teaches problem-solving, basic syntax, and algorithmic logic from scratch with dedicated 1:1 mentorship, protecting you from pacing dropouts."
            )

    # 0c. Legal, Compliance & Judiciary (Lawyer, Advocate, Legal Counsel, Compliance)
    if match_any(r_lower, ['lawyer', 'advocate', 'attorney', 'legal', 'paralegal', 'solicitor', 'barrister', 'judge', 'magistrate', 'compliance']):
        if 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your deep expertise in evidence synthesis, case precedent analysis, and statutory interpretation "
                "provides an analytical edge in structured SQL querying, legal compliance analytics, and NLP-driven document intelligence."
            )
        elif 'agentic' in p_lower or 'aiml' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), pairing your legal reasoning and contract structuring with Agentic AI and LegalTech LLM automation "
                "positions you at the forefront of AI-driven legal intelligence."
            )
        else:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), statutory law is fundamentally rule-based logic, conditionals (IF-THEN-ELSE), and exception handling. "
                "This structured thinking maps directly into software engineering and algorithmic problem-solving."
            )

    # 0d. Education, Teaching & Academia
    if match_any(r_lower, ['teacher', 'professor', 'lecturer', 'tutor', 'educator', 'faculty', 'instructor', 'academic', 'principal']):
        if 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As an <b>{raw_role}</b> ({raw_exp}), your pedagogical training and ability to break down complex concepts into structured lessons "
                "translate seamlessly into data storytelling, visual dashboards, and educational analytics."
            )
        else:
            return (
                f"As an <b>{raw_role}</b> ({raw_exp}), your habit of structured curriculum design and systematic lesson planning "
                "gives you the patience and learning discipline to master programming logic, algorithms, and software development from ground up."
            )

    # 0e. Transportation, Aviation & Maritime (Pilot, Sailor, Driver, Logistics)
    if (match_any(r_lower, ['pilot', 'mariner', 'sailor', 'merchant navy', 'ship captain', 'loco pilot', 'train driver', 'truck driver', 'cab driver', 'taxi driver', 'courier', 'delivery partner']) or
        (match_token(r_lower, 'driver') and 'device' not in r_lower and 'software' not in r_lower and 'hardware' not in r_lower)):
        if 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your checklist discipline and experience monitoring complex navigation and telemetry systems "
                "translate naturally into SRE monitoring, cloud infrastructure operations, and automated CI/CD deployment pipelines."
            )
        elif 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your experience with route planning, telemetry data, and fuel/cargo metrics "
                "provides practical domain intuition for predictive supply-chain analytics and operational machine learning."
            )
        else:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your operational composure and systematic checklist execution "
                "help you build reliable, disciplined software development and debugging habits."
            )

    # 0f. Product Management, UI/UX & Agile Delivery
    if match_any(r_lower, ['product manager', 'apm', 'tpm', 'product owner', 'scrum master', 'agile', 'ui/ux', 'ux designer', 'product designer']):
        if 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), you already define product requirements and track feature adoption metrics. "
                "This track empowers you with SQL data extraction, cohort retention analytics, and A/B test predictive modeling to make data-driven product decisions."
            )
        elif 'fde' in p_lower or 'forward deployed' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), pairing your product leadership and stakeholder roadmap execution with "
                "Enterprise AI deployment makes you an ideal Forward Deployed AI Engineer."
            )
        else:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), learning software architecture, API design, and data structures bridges the technical communication gap with engineering teams."
            )

    # 0g. Skilled Trades & Construction Maintenance
    if match_any(r_lower, ['electrician', 'plumber', 'welder', 'machinist', 'carpenter', 'mason', 'construction', 'builder', 'painter', 'hvac', 'tailor']):
        if 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your practical troubleshooting and physical systems maintenance experience "
                "translate naturally into cloud infrastructure management, server provisioning, and network cabling/hardware operations."
            )
        else:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this Beginner Track teaches technical problem-solving and programming syntax "
                "from ground zero, providing step-by-step guidance to build professional software skills."
            )

    # 1. Finance / Accounting / Banking / Audit / CA
    if match_any(r_lower, ['account', 'finance', 'auditor', 'banking', 'ca', 'chartered', 'tax', 'bookkeeper', 'treasury', 'financial']):
        if 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As an <b>{raw_role}</b> ({raw_exp}), you already work with numerical data, spreadsheets, and financial reports daily. "
                "This program builds directly on your existing analytical mindset by transforming spreadsheet modeling into SQL queries, "
                "Python automation, and predictive machine learning models."
            )
        elif 'academy' in p_lower or 'software' in p_lower:
            return (
                f"As an <b>{raw_role}</b> ({raw_exp}), your daily discipline with structured financial calculations, reconciliation logic, "
                "and numeric precision provides a strong foundation for computational thinking, algorithmic logic, and software development."
            )
        elif 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As an <b>{raw_role}</b> ({raw_exp}), this program offers a practical, tools-oriented technical pivot focusing on "
                "Linux, cloud infrastructure, and automation scripts without requiring abstract mathematical puzzles."
            )
        elif 'agentic' in p_lower or 'aiml' in p_lower:
            return (
                f"As an <b>{raw_role}</b> ({raw_exp}), your numerical exposure aligns with building domain-specific financial AI agents, "
                "prompt automations, and LLM data pipelines."
            )

    # 2. Healthcare / Clinical / Medical / Pharmacy
    if any(k in r_lower for k in ['nurse', 'nursing', 'doctor', 'hospital', 'physician', 'dentist', 'pharmacist', 'paramedic', 'medical', 'clinic']):
        if 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your familiarity with patient records, clinical workflows, and diagnostic patterns "
                "translates directly into healthcare data analytics, statistical modeling, and predictive AI."
            )
        elif 'academy' in p_lower or 'software' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your background in executing high-precision clinical protocols and diagnostic decision-making "
                "translates naturally into structured computational thinking, step-by-step logic, and software engineering."
            )
        elif 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this program provides an accessible entry into tech through hands-on labs and "
                "cloud infrastructure automation with 1:1 mentorship."
            )

    # 3. Operations / Supply Chain / Logistics / Admin / Procurement
    if (any(k in r_lower for k in ['operation', 'logistics', 'supply chain', 'procurement', 'inventory', 'warehouse', 'coordinator']) or
        (match_token(r_lower, 'admin') and not any(t in r_lower for t in ['database', 'dba', 'sysadmin', 'system', 'linux', 'network', 'cloud', 'azure', 'aws']))):
        if 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As an <b>{raw_role}</b> ({raw_exp}), you already manage operational metrics, workflow pipelines, and inventory data daily. "
                "This program transforms that operational acumen into structured SQL data pipelines, visual dashboarding, and predictive analytics."
            )
        elif 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As an <b>{raw_role}</b> ({raw_exp}), your background in managing end-to-end operational pipelines aligns directly with "
                "CI/CD automation, workflow orchestration, and cloud infrastructure management."
            )
        elif 'academy' in p_lower or 'software' in p_lower:
            return (
                f"As an <b>{raw_role}</b> ({raw_exp}), your experience in workflow optimization and system bottleneck resolution "
                "gives you an intuitive grasp of algorithmic processes and backend system design."
            )

    # 3b. Category Management / Merchandising / E-Commerce / Pricing
    if any(k in r_lower for k in ['category', 'merchandis', 'catalog', 'pricing', 'e-commerce', 'ecommerce', 'retail manager', 'store manager']):
        if 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), you already work with business KPIs, supply-demand metrics, pricing, and vendor data daily. "
                "This program translates that commercial intuition into advanced SQL pipelines, product analytics dashboards, and predictive machine learning models "
                "to accelerate you into Senior Product Analyst, Analytics Manager, and Business Data Science roles."
            )
        elif 'academy' in p_lower or 'software' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this program pairs your commercial problem-solving and business workflow acumen with "
                "foundational programming syntax, algorithmic logic building, and computational thinking from ground zero."
            )
        elif 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this program provides an accessible technical pivot into cloud infrastructure, "
                "Linux automation, and deployment pipelines without requiring abstract software design."
            )
        else:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this track builds the technical foundation to bridge your commercial management experience into tech."
            )

    # 4. Sales / Marketing / Growth / Business Development
    if any(k in r_lower for k in ['sales', 'marketing', 'bde', 'bda', 'growth', 'business dev', 'account manager']):
        if 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), you already understand customer funnels, campaign metrics, and business drivers. "
                "This program supercharges that commercial instinct with SQL queries, product analytics, and predictive customer modeling."
            )
        elif 'fde' in p_lower or 'forward deployed' in p_lower or 'agentic' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), pairing your strong client communication and stakeholder management with "
                "enterprise AI deployment creates a high-leverage Forward Deployed Engineer profile."
            )
        else:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this program takes your commercial communication skills and pairs them with "
                "computational thinking and coding from scratch to build client-ready software products."
            )

    # 5. HR / People Ops / Recruitment
    if any(k in r_lower for k in ['hr', 'human resource', 'recruiter', 'talent', 'people ops']):
        if 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As an <b>{raw_role}</b> ({raw_exp}), you already handle workforce information and recruitment metrics. "
                "This program formalizes your reporting into SQL data pipelines, People Analytics, and predictive talent modeling."
            )
        else:
            return (
                f"As an <b>{raw_role}</b> ({raw_exp}), this Beginner Track starts from absolute fundamentals, "
                "building coding habits and computational logic step-by-step."
            )

    # 6. Core Engineering (Mechanical, Civil, Electrical, Chemical, Electronics)
    if any(k in r_lower for k in ['mechanical', 'civil', 'chemical', 'electrical', 'biotech', 'aerospace', 'automobile', 'electronics']):
        if 'academy' in p_lower or 'software' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your core engineering mathematics and physical systems background "
                "give you a massive quantitative advantage in understanding algorithms, data structures, and system design."
            )
        elif 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your engineering math and scientific modeling training translate seamlessly "
                "into statistical data science, Python computing, and machine learning."
            )
        elif 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your background in physical systems and infrastructure makes "
                "cloud architecture, container clustering, and Linux automation a natural technical pivot."
            )

    # 7. Customer Support / Technical Support / BPO / Helpdesk / Operations Support
    if any(k in r_lower for k in ['support', 'bpo', 'kpo', 'helpdesk', 'service desk', 'customer care', 'call center', 'operations support', 'it support', 'desktop support']):
        if 'academy' in p_lower or 'software' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your hands-on experience troubleshooting technical issues and debugging application workflows "
                "gives you practical domain intuition into software systems. This program equips you with core Data Structures, algorithmic problem-solving, "
                "and backend engineering from ground up to transition from reactive ticket resolution into proactive software development (SDE)."
            )
        elif 'fde' in p_lower or 'forward deployed' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), you already understand real-world customer pain points and system integrations daily. "
                "The Forward Deployed Engineering track leverages your customer-facing technical support background into deploying production AI systems, "
                "automating enterprise support workflows with LangGraph and RAG, and integrating custom solutions directly inside client infrastructure."
            )
        elif 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your technical troubleshooting and ticket triage background translate directly "
                "into production incident management, SRE monitoring, automated alerting, and CI/CD cloud operations."
            )
        elif 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this track builds on your issue resolution and system ticketing experience by equipping you with "
                "SQL querying, product usage analytics, customer churn modeling, and automated business dashboards."
            )
        elif 'agentic' in p_lower or 'aiml' in p_lower:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), your frontline support domain experience is prime for enterprise LLM automation—building "
                "autonomous customer resolution agents, multi-turn LangGraph workflows, and retrieval-augmented generation (RAG) pipelines."
            )
        else:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this track provides a structured, guided bridge from operational support into "
                "high-growth software engineering and technology leadership."
            )

    # 8. QA / SDET / Testing
    if any(k in r_lower for k in ['qa', 'test', 'sdet', 'quality']):
        if 'academy' in p_lower or 'software' in p_lower:
            if 'advanced' in t_lower or 'leadership' in t_lower:
                return (
                    f"As a senior <b>{raw_role}</b> with {raw_exp}, you have mastered quality lifecycles and enterprise systems; "
                    "this track focuses on High-Level Distributed System Design (HLD), event streaming, and architectural scalability "
                    "commanded in Principal Architect and Engineering Leadership roles."
                )
            else:
                return (
                    f"As a <b>{raw_role}</b> with {raw_exp}, you already understand software lifecycles and code structures; "
                    "this track bridges the exact gap in algorithmic optimization, advanced DSA, and low-level object-oriented design (LLD) "
                    "to transition into core Backend SDE roles."
                )
        elif 'fde' in p_lower or 'forward deployed' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, your deep enterprise systems and quality assurance background translates directly "
                "into deploying reliable, enterprise-grade AI applications, agent evaluation frameworks, and client systems integration."
            )
        elif 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, your test automation background translates directly into "
                "CI/CD pipelines, containerized test runners, and cloud infrastructure management."
            )
        elif 'dsml' in p_lower or 'agentic' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, moving into AI/ML enables you to apply your testing rigor to "
                "AI model evaluation, data pipelines, and intelligent agent workflows."
            )

    # 9. Data Analyst / BI / Reporting
    if any(k in r_lower for k in ['data analyst', 'business analyst', 'bi analyst', 'analytics', 'tableau', 'power bi', 'sql developer']):
        if 'dsml' in p_lower or 'data' in p_lower:
            if 'beginner' in t_lower or 'analytics' in t_lower:
                return (
                    f"As a <b>{raw_role}</b> with {raw_exp}, you already have reporting exposure; this track solidifies your "
                    "foundational analytics, Python automation, and product metrics to prepare you for machine learning workflows."
                )
            else:
                return (
                    f"As a <b>{raw_role}</b> with {raw_exp}, you already write SQL queries and build dashboards daily; "
                    "this track breaks through the reporting salary ceiling by adding predictive modeling, deep neural networks, and production MLOps on AWS."
                )
        elif 'agentic' in p_lower or 'aiml' in p_lower or 'fde' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, expanding from SQL and dashboards into Agentic AI, GraphRAG, and "
                "LangGraph multi-agent orchestration elevates your profile to frontier AI engineering roles."
            )
        elif 'academy' in p_lower or 'software' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, adding core data structures, algorithms, and backend API engineering "
                "turns you into a full-stack data and software engineer."
            )

    # 10. Software Engineer / SDE / Web Developer
    if any(k in r_lower for k in ['sde', 'software', 'developer', 'frontend', 'backend', 'full stack', 'programmer', 'web dev']):
        if 'academy' in p_lower or 'software' in p_lower:
            if 'intermediate' in t_lower or 'dsa' in t_lower:
                return (
                    f"As a <b>{raw_role}</b> with {raw_exp}, you already know how to code. "
                    "This is the Intermediate batch for learners with basic coding experience."
                )
            elif 'advanced' in t_lower:
                return (
                    f"As a <b>{raw_role}</b> with {raw_exp}, you have mastered coding and team delivery - but the next level (Staff Engineer, Principal Architect) "
                    "demands large-scale distributed systems expertise (Kafka, consistent hashing, database sharding, CAP/PACELC)."
                )
            else:
                return (
                    f"As a <b>{raw_role}</b> with {raw_exp}, this track builds structured problem-solving and algorithmic thinking "
                    "that Tier-1 product companies test rigorously in interviews."
                )
        elif 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, expanding into Cloud & DevOps complements your development background with "
                "Docker, Kubernetes, CI/CD automation, and Terraform IaC."
            )
        elif 'fde' in p_lower or 'forward deployed' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, FDE is a role focused on building AND deploying custom LLM systems "
                "inside enterprise client infrastructure with LangGraph and Meridian simulation."
            )
        elif 'agentic' in p_lower or 'aiml' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, moving from backend engineering into AI and machine learning engineering "
                "builds on your current skills toward AI Engineer roles."
            )
        elif 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, your coding syntax and software foundation let you bypass basic Python "
                "and advance directly into statistical modeling, feature engineering pipelines, and production machine learning at scale."
            )

    # 11. DevOps / Cloud / SRE / SysAdmin
    if any(k in r_lower for k in ['devops', 'cloud', 'sre', 'sysadmin', 'system admin', 'infrastructure', 'platform engineer']):
        if 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, modernizing your infrastructure skillset with Kubernetes clustering, "
                "Terraform GitOps, and AWS cloud architecture elevates you into senior Platform Engineer and SRE roles."
            )
        elif 'academy' in p_lower or 'software' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, adding core data structures, algorithms, and backend microservices design "
                "rounds out your engineering profile to clear Tier-1 software and platform engineering rounds."
            )
        elif 'agentic' in p_lower or 'aiml' in p_lower or 'dsml' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, expanding into MLOps and AI agent infrastructure "
                "points toward AI Infrastructure and LLMOps roles."
            )

    # 11b. Systems & Embedded Engineering (Systems Engineer, Embedded, Firmware, Hardware, IoT, Device Driver)
    if any(k in r_lower for k in ['system', 'embedded', 'firmware', 'hardware', 'vlsi', 'iot', 'kernel', 'device driver']):
        if 'academy' in p_lower or 'software' in p_lower:
            if 'advanced' in t_lower or 'leadership' in t_lower:
                return (
                    f"As a <b>{raw_role}</b> with {raw_exp}, your low-level hardware and memory control provide an exceptional foundation; "
                    "this track focuses on High-Level Distributed System Design (HLD), event streaming, database sharding, and architectural scalability "
                    "commanded in Principal Systems Architect and Staff Engineer roles."
                )
            else:
                return (
                    f"As a <b>{raw_role}</b> with {raw_exp}, your C/C++ memory management and low-level computing background "
                    "give you an intuitive edge in mastering competitive Data Structures, Algorithms, and modern backend microservices."
                )
        elif 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, your deep OS, Linux, and hardware experience translates directly into "
                "bare-metal server orchestration, Kubernetes cluster operations, and high-performance cloud platform engineering."
            )
        elif 'fde' in p_lower or 'forward deployed' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, your systems depth is crucial for deploying low-latency AI models, "
                "optimizing inference pipelines on custom client hardware, and integrating enterprise agent architectures."
            )
        elif 'dsml' in p_lower or 'agentic' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, your hardware and mathematical background lets you master "
                "model quantization, edge AI deployment, and high-throughput machine learning feature pipelines."
            )

    # 11c. Cybersecurity, InfoSec & Network Security
    if any(k in r_lower for k in ['cyber security', 'cybersecurity', 'security', 'infosec', 'soc analyst', 'penetration', 'appsec', 'network security']):
        if 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, your threat analysis and security governance background translates directly into "
                "DevSecOps, automated vulnerability scanning, cloud IAM architecture, and secure Kubernetes deployment."
            )
        elif 'academy' in p_lower or 'software' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, adding core data structures, algorithms, and backend API engineering "
                "qualifies you for high-paying Secure Software Engineering and Application Security (AppSec) architect roles."
            )
        elif 'agentic' in p_lower or 'aiml' in p_lower or 'fde' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, your security mindset is crucial for securing enterprise LLM pipelines, "
                "defending against prompt injection, and implementing robust multi-agent security guardrails."
            )

    # 11d. Database Administrator / DBA
    if any(k in r_lower for k in ['dba', 'database administrator', 'database engineer', 'oracle dba', 'sql dba']):
        if 'academy' in p_lower or 'software' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, your deep relational database internals, query optimization, and storage indexing "
                "give you an unfair advantage in High-Level System Design, distributed database sharding, and backend microservices architecture."
            )
        elif 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, your database reliability and backup/recovery experience maps directly into "
                "Cloud Database Operations, automated Terraform provisioning, and site reliability engineering."
            )
        elif 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, your SQL mastery enables an effortless transition into large-scale "
                "Data Engineering, PySpark ETL pipelines, and predictive machine learning feature stores."
            )

    # 11e. Engineering Leadership & Technical Architects
    if any(k in r_lower for k in [
        'tech lead', 'technical lead', 'team lead', 'engineering manager', 'director', 'cto', 'architect',
        'engineering leadership', 'tech leadership', 'technical leadership', 'software leadership', 'leadership'
    ]):
        if 'academy' in p_lower or 'software' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, this track sharpens your architectural authority - mastering distributed systems scalability, "
                "event-driven microservices (Kafka), database sharding, and high-level design patterns commanded in Staff and Principal Architect roles."
            )
        elif 'fde' in p_lower or 'forward deployed' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, pairing your technical leadership and delivery governance with "
                "client-facing AI deployment positions you as a high-compensation Forward Deployed Engineering leader."
            )
        elif 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, modernizing your infrastructure strategy with Kubernetes, multi-region cloud resilience, "
                "and GitOps automation equips you to lead modern cloud engineering organizations."
            )
        elif 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b> with {raw_exp}, this track equips you to direct enterprise ML strategy — translating predictive modeling, "
                "deep learning architectures, and scalable AWS MLOps into high-impact organizational capabilities to lead modern data science teams."
            )

    # 12. Freshers / Students
    if any(k in r_lower for k in ['fresher', 'student', 'intern', 'college student', 'final year']) or any(k in str(raw_exp).lower() for k in ['fresher', 'entry', 'no exp']) or str(raw_exp).strip() in ['0', '0 yrs', '0.0 yrs']:
        if ('academy' in p_lower or 'software' in p_lower) and ('intermediate' in t_lower or 'advanced' in t_lower):
            level = 'Advanced' if 'advanced' in t_lower else 'Intermediate'
            return (
                f"As a <b>{raw_role}</b> who has already started coding, the {level} batch builds on what you know "
                "with data structures, algorithms and system design, instead of starting from the basics."
            )
        if 'academy' in p_lower or 'software' in p_lower:
            return (
                f"As a <b>{raw_role}</b>, this Beginner Track takes you from absolute zero to interview-ready software engineer. "
                "It builds computational thinking, problem-solving, and coding fundamentals from scratch - the exact skills Tier-1 product companies test in every interview."
            )
        elif 'dsml' in p_lower or 'data' in p_lower:
            return (
                f"As a <b>{raw_role}</b>, this track is the smoothest entry into tech because it does NOT assume any coding background. "
                "It starts with Excel, SQL queries, and visual dashboards before gradually introducing Python and machine learning."
            )
        elif 'devops' in p_lower or 'cloud' in p_lower:
            return (
                f"As a <b>{raw_role}</b>, DevOps & Cloud Engineering is an accessible entry point into tech focusing on "
                "practical tools, Linux scripting, Docker, and AWS rather than competitive algorithmic problem-solving."
            )
        else:
            return (
                f"As a <b>{raw_role}</b>, this track provides a structured ramp-up into high-growth technology careers."
            )

    # Intelligent Career Alignment (Role & Experience Aware)
    if 'fde' in p_lower or 'forward deployed' in p_lower:
        return (
            f"As a <b>{raw_role}</b> ({raw_exp}), combining your practical problem-solving with client-facing enterprise AI integration "
            "accelerates you into high-compensation Forward Deployed Engineer roles delivering custom LLM systems and production LangGraph pipelines."
        )
    elif 'devops' in p_lower or 'cloud' in p_lower:
        return (
            f"As a <b>{raw_role}</b> ({raw_exp}), this track equips you with hands-on container orchestration (Kubernetes), "
            "cloud infrastructure-as-code (Terraform), and automated CI/CD pipelines to step into modern Platform Engineering."
        )
    elif 'dsml' in p_lower or 'data' in p_lower:
        if any(k in r_lower for k in ['data scientist', 'machine learning', 'ml engineer', 'ai engineer', 'statistician']):
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this track elevates your predictive modeling expertise into production-grade ML systems—covering "
                "deep learning neural architectures, mathematical AI foundations, and scalable MLOps pipelines."
            )
        elif any(k in r_lower for k in ['analyst', 'analytics', 'bi', 'tableau', 'power bi', 'business analyst']):
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this track translates your analytics foundation into predictive data science—teaching "
                "advanced statistical modeling, Python data engineering at scale, and applied machine learning."
            )
        else:
            return (
                f"As a <b>{raw_role}</b> ({raw_exp}), this track translates your domain experience into data-driven decision making—teaching "
                "SQL data querying, business metrics dashboards, and applied predictive machine learning."
            )
    elif 'agentic' in p_lower or 'aiml' in p_lower:
        return (
            f"As a <b>{raw_role}</b> ({raw_exp}), this curriculum fast-tracks your profile into modern Agentic AI, "
            "retrieval-augmented generation (RAG), and production LLMOps."
        )
    else:
        return (
            f"As a <b>{raw_role}</b> ({raw_exp}), this program provides a structured curriculum that bridges your current experience "
            "into core software development, algorithmic problem-solving, and scalable system design."
        )


SHOW_COHORT_EVIDENCE_ON_CARD = False   # the observed refund numbers stay in the data but are not shown on the card


_SOFTEN = [
    ("elevates your profile to frontier AI engineering roles", "builds on your current skills toward AI engineering roles"),
    ("positions you for high-paying AI Engineer roles", "points toward AI Engineer roles"),
    ("qualifies you for high-paying Secure Software Engineering", "points toward Secure Software Engineering"),
    ("elevates you into senior Platform Engineer and SRE roles", "points toward Platform Engineer and SRE roles"),
    ("elevates your predictive modeling expertise into", "extends your predictive modeling expertise into"),
    ("fast-tracks your profile into", "moves your profile into"),
    ("focuses directly on high-demand domain application", "covers a different domain"),
    ("elevates you into", "moves you into"),
    ("elevates this into", "extends this into"),
    ("high-paying ", ""),
    ("high-demand ", ""),
    ("frontier AI", "advanced AI"),
    ("Frontier AI", "Advanced AI"),
    ("highest-leverage", "suggested"),
]


def soften_claims(text):
    """Remove sales wording that no source supports (pay, demand and 'elevate' claims)."""
    out = str(text or "")
    for a, b in _SOFTEN:
        out = out.replace(a, b)
    return out


def clean_exp_text(raw_exp):
    """Experience as a phrase for sentences: 'About 4 yrs (With Deloitte since 2022)' -> 'about 4 yrs of experience'."""
    t = str(raw_exp or "").strip()
    m_batch = re.match(r"^\s*(?:about\s+)?([\d.]+)\s*(?:yrs?|years?)\s*\(Batch\s*(\d{4})\)", t, re.I)
    if m_batch:
        return f"about {m_batch.group(1)} yrs since graduating in {m_batch.group(2)}"
    m_since = re.match(r"^\s*(?:about\s+)?([\d.]+)\s*(?:yrs?|years?)\s*\((?:With[^)]*?)?since\s*(\d{4})\)", t, re.I)
    if m_since:
        return f"about {m_since.group(1)} yrs since joining their organisation in {m_since.group(2)}"
    t = re.sub(r"\s*\((?:With|Batch)[^)]*\)", "", t).strip()
    if re.search(r"\b(yrs?|years?)\b", t, re.I):
        t = re.sub(r"\s*\(\d+(?:\.\d+)?\s*mos?\)", "", t).strip()      # '4 yrs (48 mos)' -> '4 yrs' 
    if re.match(r"^(about\s+)?[\d.]+\s*(yrs?|years?)\b", t, re.I) and "experience" not in t.lower():
        t = t[0].lower() + t[1:] + " of experience"
    return t


def cohort_evidence_text(cohort_detail, retention_rate, cohort_size):
    """How the refund numbers were obtained. Kept in the data (card['cohort_evidence']) but not shown on the card."""
    if cohort_detail:
        d = cohort_detail
        historical_desc = (
            f"{d['refunds']} of the {d['n']} most similar past learners in this program requested a refund ({d['refund_rate']}%). "
            f"Matched on: {d['basis']}"
            + (f" ({d['exact_available']} learners match the persona and experience band exactly; the newest {d['exact_used']} are used)."
               if d['exact_used'] == d['n'] and d['exact_available'] > d['n'] else
               (f" ({d['exact_available']} learners match the persona and experience band exactly)." if d['exact_available'] else "."))
        )
        if d['exact_available'] < 30:
            historical_desc += " Few exact matches, so read it with caution."
    else:
        historical_desc = (
            f"Estimated {retention_rate}% retention ({round(100 - float(retention_rate), 1)}% refund) from {cohort_size} past learners in this program, "
            f"persona and experience group. The rate is adjusted toward the program average, so it is an estimate, not a raw count."
        )
    return historical_desc


def generate_curriculum_grounded_why(
    program_name, track_name, raw_role, raw_exp, modules,
    retention_rate, cohort_size, fit_tier, inbound_cat,
    is_primary=True, base_rationale="", persona="", primary_prog_name="", cohort_detail=None
):
    """
    Synthesizes a cohesive, curriculum-grounded explanation for 'Why This Program' / 'Why Fallback'.
    Grounds the reasoning directly in the candidate's current role, experience level, and career trajectory.
    """
    p_lower = str(program_name).lower()
    t_lower = str(track_name).lower()
    raw_exp = clean_exp_text(raw_exp)

    # 1. Career Pitch grounded in candidate's current role
    raw_career_desc = soften_claims(generate_role_pitch(raw_role, raw_exp, p_lower, t_lower, is_primary, persona))
    if persona == 'NON_TECH' and ('agentic' in p_lower or 'machine learning' in p_lower) and 'beginner' in t_lower and 'data science' not in p_lower and 'dsml' not in p_lower:
        # Program 4's Beginner Track for a non-tech lead: speak to a beginner, whatever the current role
        raw_career_desc = soften_claims(
            f"As {'an' if str(raw_role).strip()[:1].lower() in 'aeiou' else 'a'} <b>{raw_role}</b> ({raw_exp}), this Beginner Track needs no prior coding. It starts with Python and the maths you need, "
            "then builds up to machine learning, large language models and AI agents."
        )

    if is_primary:
        career_desc = raw_career_desc
    else:
        # For Fallback, craft a smooth transition contrasting with Primary
        if primary_prog_name and 'academy' in str(primary_prog_name).lower():
            contrast_prefix = (
                f"While <b>{primary_prog_name}</b> is your primary route for core software engineering interviews, "
                f"<b>{program_name}</b> is the alternative path. "
            )
        elif primary_prog_name:
            contrast_prefix = (
                f"If you choose not to pursue <b>{primary_prog_name}</b>, "
                f"<b>{program_name}</b> is the alternative route. "
            )
        else:
            contrast_prefix = "As an alternative strategic pathway, "
        
        career_desc = soften_claims(f"{contrast_prefix}{raw_career_desc}")

    # 2. Extract top module phases for Curricular Milestones
    module_names = []
    if modules and isinstance(modules, list):
        for m in modules[:5]:
            p = m.get('phase', '')
            if p and p not in module_names:
                module_names.append(p)

    # 3. Standardized, high-impact curricular content descriptions by program
    if 'academy' in p_lower or 'software' in p_lower:
        if 'beginner' in t_lower or 'foundations' in t_lower:
            content_desc = (
                "Features foundational modules starting with <i>Programming Fundamentals - Thinking with AI (Logics, Loops & Control Flow)</i>, "
                "<i>Intermediate DSA (Prefix Sum, Bit Manipulation, 2D Matrices)</i>, and <i>AI & Agents: From Talking to AI to Building One</i>, "
                "before advancing into <i>Advanced DSA</i> (Linear/Non-Linear Structures, Trees, Dynamic Programming, Graphs) and <i>System Design</i>."
            )
            historical_desc = (
                f"Backed by an audited <b>{retention_rate}% completion rate</b> across {cohort_size}+ early-career and non-CS learners. "
                "Beginners placed directly into intermediate algorithms face elevated Day-14 pacing dropout; this structured ramp-up prevents that."
            )
        elif 'intermediate' in t_lower or 'dsa' in t_lower:
            content_desc = (
                "Bypasses basic syntax to focus directly on <i>Intermediate DSA : AI Assisted Problem Solving</i>, "
                "<i>Advanced DSA (Divide & Conquer, Trees, Heaps, Graphs, Dynamic Programming)</i>, and <i>Low-Level Object-Oriented Design (LLD)</i>, "
                "with an elective bridge into <i>Distributed High-Level System Design</i>."
            )
            historical_desc = (
                f"Supported by an empirical <b>{retention_rate}% completion rate</b> across {cohort_size}+ working technical professionals. "
                ""
            )
        else: # Advanced
            content_desc = (
                "The Advanced batch is for learners with notable coding experience. The syllabus is in the program brochure."
            )
            historical_desc = ""

    elif 'dsml' in p_lower or 'data science' in p_lower:
        if 'beginner' in t_lower or ('analytics' in t_lower and 'machine' not in t_lower and 'core' not in t_lower and 'intermediate' not in t_lower):
            content_desc = (
                "Begins with <i>Advanced SQL & AI for Data Professionals</i>, <i>Excel & Dashboarding with AI Storytelling</i>, "
                "<i>Python Foundations + AI Coding Assistants</i>, and <i>Product Analytics with AI</i>, seamlessly progressing into "
                "<i>Supervised Machine Learning with AI Workflows</i>."
            )
            historical_desc = (
                f"Proven by a <b>{retention_rate}% completion rate</b> across {cohort_size}+ learners. "
                ""
            )
        else: # Intermediate / Core ML / Advanced
            content_desc = (
                "Dives directly into <i>Advanced Analytics with Python & Pandas</i>, <i>Statistics & Experimentation for AI (A/B Testing Frameworks)</i>, "
                "<i>Supervised & Unsupervised Machine Learning</i>, <i>Deep Learning & Neural Networks</i>, and <i>Production MLOps on AWS</i>."
            )
            # Persona-aware cohort retention blurb
            _is_leadership = any(k in persona.lower() for k in ['leadership', 'leader']) if persona else False
            if _is_leadership:
                historical_desc = (
                    f"Validated by an audited <b>{retention_rate}% completion rate</b> across senior engineering cohorts. "
                    "Technical leaders advancing through production ML and MLOps experience rapid impact scaling machine learning initiatives."
                )
            else:
                historical_desc = (
                    f"Validated by an audited <b>{retention_rate}% completion rate</b> across quantitative cohorts. "
                    "Analysts transitioning through predictive modeling experience rapid career acceleration into senior ML titles."
                )

    elif 'fde' in p_lower or 'forward deployed' in p_lower:
        content_desc = (
            "Delivered entirely through enterprise client simulation (<i>Meridian Platform</i>), covering <i>The Ingestion Pipeline (Production Python)</i>, "
            "<i>Production RAG for Customer Support</i>, <i>Autonomous Agents & Enterprise Integration (LangGraph & MCP)</i>, "
            "<i>Docker & Kubernetes Orchestration</i>, and <i>1-Click AWS Production Deployment with Terraform</i>."
        )
        historical_desc = (
            f"Supported by an outstanding <b>{retention_rate}% completion rate</b> across software engineering cohorts. "
            "Forward-deployed roles command a 2.5x compensation premium over traditional development due to high client demand."
        )

    elif 'agentic' in p_lower or 'aiml' in p_lower or 'program 4' in p_lower:
        if 'beginner' in t_lower or 'foundation' in t_lower:
            content_desc = (
                "Includes the dedicated 2-Month <i>Generative AI Foundations & LLM Landscape</i> (Prompt Engineering, n8n/Zapier automations, no-code agents, AWS hosting) "
                "and 1-Month <i>Python Programming Fundamentals</i>, before advancing into <i>Data Foundations</i>, <i>Supervised/Unsupervised ML</i>, "
                "<i>MLOps on AWS SageMaker</i>, and <i>LangGraph Agentic Orchestration</i>."
            )
            historical_desc = (
                f"Candidates without prior coding exposure face a 25.8% drop-off if pushed directly into tensor math; "
                f"this foundational progression preserves high retention (<b>{retention_rate}% completion rate</b> across {cohort_size}+ learners)."
            )
        else: # Advanced Track
            content_desc = (
                "Bypasses introductory syntax to dive directly into <i>Data Foundations</i>, <i>Applied Deep Learning (OpenCV & Transformers)</i>, "
                "<i>MLOps on AWS SageMaker</i>, <i>Agentic Design Patterns & LangGraph Multi-Agent Orchestration</i>, "
                "<i>Advanced Cognitive Architectures (GraphRAG & Multimodal AI)</i>, and <i>PEFT/LoRA Fine-Tuning served via vLLM</i>."
            )
            historical_desc = (
                f"Backed by an empirical <b>{retention_rate}% completion rate</b> across technical cohorts. "
                "Software developers thrive when immersed directly in modern generative AI architectures and scalable LLMOps."
            )

    elif 'devops' in p_lower or 'cloud' in p_lower or 'platform' in p_lower or 'program 5' in p_lower:
        content_desc = (
            "Systematically covers the entire modern platform stack: <i>Python & Linux Shell Scripting (1 & 2)</i>, "
            "<i>DevOps Tools 1 (Docker, multi-node Kubernetes clustering, Prometheus/Grafana monitoring, Hugging Face model deployment)</i>, "
            "<i>DevOps Tools 2 (GitHub Actions CI/CD, ArgoCD GitOps, Ansible)</i>, and <i>AWS 1 & 2 (EKS, VPC, CloudFormation, Terraform IaC)</i>, "
            "with specialized electives in <i>MLOps & AI Observability</i>."
        )
        historical_desc = (
            f"Demonstrates an elite <b>{retention_rate}% completion rate</b> ({cohort_size}+ cohort). "
            "Infrastructure and platform engineering provides the highest retention and lowest refund rate among all technical transitions."
        )

    else:
        module_text = ", ".join(f"<i>{h}</i>" for h in module_names[:3]) if module_names else "core engineering and production milestones"
        content_desc = f"Curriculum structured around {module_text}."
        historical_desc = f"Supported by a {retention_rate}% completion rate across {cohort_size}+ learners."

    if modules and isinstance(modules, list):
        items = [(f"{m.get('phase')} ({m.get('duration')})" if m.get('duration') else str(m.get('phase'))) for m in modules[:8] if m.get('phase')]
        more = len(modules) - len(items)
        content_desc = "Modules in this track's outline (from the program brochure): " + "; ".join(items) + (f"; and {more} more." if more > 0 else ".")
    else:
        content_desc = "The module outline is in the program brochure."
    historical_desc = cohort_evidence_text(cohort_detail, retention_rate, cohort_size)
    if not SHOW_COHORT_EVIDENCE_ON_CARD:
        return career_desc
    full_rationale = (
        f"{career_desc}<br><br>"
        f"<b>Curricular Content & Milestones:</b> {content_desc}<br><br>"
        f"<b>Historical Retention & Cohort Evidence:</b> {historical_desc}"
    )
    return full_rationale


def _cohort_stats(program_lookup, persona, exp_bracket, matrix_data):
    """Observed refund numbers for the nearest past learners; the smoothed matrix is only a fallback when no outcomes file exists."""
    m = match_cohort(program_lookup, persona, exp_bracket) if cohort_available() else None
    if m:
        return {
            'retention_rate': m['retention_rate'], 'refund_rate': m['refund_rate'], 'total': m['n'],
            'refunds': m['refunds'], 'exact_available': m['exact_available'], 'detail': m,
        }
    st = get_cohort_stats(program_lookup, persona, exp_bracket, matrix_data)
    return dict(st, exact_available=st.get('total', 0), refunds=None, detail=None)


def _evaluate_core(lead_dict, matrix_data=None, force_inbound=None):
    """
    Evaluates a lead profile against the official 5-Program Scaler Catalog.
    Includes Education Prerequisite Gate, Persona Taxonomy, and spoken sales scripts.
    """
    def _field(keys, default=''):
        for k in keys:
            if k in lead_dict and lead_dict[k] is not None:
                val = str(lead_dict[k]).strip()
                if val and val.lower() not in ['nan', 'none', 'null']:
                    return val
        ld_lower = {str(k).strip().lower(): v for k, v in lead_dict.items() if v is not None}
        for k in keys:
            kl = k.lower()
            if kl in ld_lower:
                val = str(ld_lower[kl]).strip()
                if val and val.lower() not in ['nan', 'none', 'null']:
                    return val
        return default

    name = clean_str(_field(['name', 'full_name', 'candidate_name', 'student_name']), 'Prospective Learner')
    email = clean_str(_field(['email', 'email_id', 'contact_email', 'lead_email']), '')
    phone = clean_str(_field(['phone', 'mobile', 'contact', 'phone_number']), 'N/A')
    raw_role_explicit = _field(['role', 'current_role', 'designation', 'job_title', 'profile', 'raw_role'], '')
    raw_exp_explicit = _field(['experience', 'yoe', 'total_experience', 'work_experience', 'exp', 'raw_exp'], '')
    raw_org_explicit = _field(['previous org name', 'previous_org_name', 'previous_org', 'company', 'organization', 'employer', 'orgname', 'raw_org', 'cand_org'], '')
    raw_comp_explicit = _field(['company type', 'company_type', 'industry', 'sector', 'cand_comp_type'], '')
    prev_year = clean_str(_field(['previous org year', 'previous_org_year', 'year', 'org_year', 'grad_year', 'graduation_year', 'orgyear']), '')
    inbound_prog_raw = clean_str(_field(['program', 'inbound_program', 'enquired_program', 'course']), 'Academy')
    inbound_given = bool(_field(['program', 'inbound_program', 'enquired_program', 'course']))
    raw_edu = clean_str(_field(['education', 'degree', 'qualification', 'highest_qualification', 'stream']), 'Graduated / Degree')
    raw_sat_status = clean_str(_field(['set_status', 'sat_status', 'diagnostic set status', 'diagnostic sat status', 'test_launched_flag']), 'SET Not Attempted')
    if 'sat' in raw_sat_status.lower():
        raw_sat_status = raw_sat_status.replace('SAT', 'SET').replace('Sat', 'Set').replace('sat', 'set')
    raw_sat_score = clean_str(_field(['set_score', 'sat_score', 'diagnostic set score', 'diagnostic sat score']), 'Not Attempted')

    # Check for College / Academic email domain (.ac.in, .edu.in, .edu, .res.in, campus subdomains)
    email_lower = str(email).lower()
    email_domain = email_lower.split('@')[-1] if '@' in email_lower else ''
    is_academic_email = any(
        email_domain.endswith(ext) for ext in ['.ac.in', '.edu.in', '.edu', '.res.in']
    ) or any(
        k in email_domain for k in ['college', 'univ', 'campus', 'student', 'institute', 'iit', 'nit', 'bits', 'vit', 'srm', 'thapar', 'manipal']
    )

    # Check if organization is a college / university / institute
    org_lower = str(raw_org_explicit).lower()
    is_academic_org = any(k in org_lower for k in [
        'college', 'university', 'institute', 'campus', 'polytechnic', 'vidyalaya',
        'iit ', 'iit-', 'nit ', 'nit-', 'bits ', 'iiit', 'vit ', 'srm '
    ])

    # Check if organization or company type is a commercial enterprise (non-academic, non-placeholder)
    raw_org_clean = str(raw_org_explicit or '').strip()
    is_empty_or_placeholder_org = raw_org_clean.lower() in [
        '', 'nan', 'none', 'null', 'not applicable', 'not applicable account',
        'student', 'na', 'n/a', '-', 'current organization', 'current company', 'fresher',
        'independent / transitioning', 'independent', 'transitioning', 'self employed',
        'freelancer', 'unemployed', 'job seeker', 'looking for job'
    ]
    has_commercial_company = bool(raw_org_clean) and (not is_empty_or_placeholder_org) and (not is_academic_org)
    comp_clean = str(raw_comp_explicit or '').strip().lower()
    if any(k in comp_clean for k in ['product', 'service', 'tech', 'startup', 'bfsi', 'enterprise', 'corporate']):
        if not is_academic_org and not is_empty_or_placeholder_org:
            has_commercial_company = True

    # Check experience numeric value and tenure
    exp_num = 0.0
    if raw_exp_explicit:
        # Strip out 4-digit calendar years (e.g. Batch 2026, 2024) so they are not treated as 2000+ years of experience!
        exp_clean_str = re.sub(r'\b(19\d\d|20\d\d)\b', '', str(raw_exp_explicit))
        m_exp = re.search(r'[-+]?\d*\.?\d+', exp_clean_str.replace(',', ''))
        if m_exp:
            try:
                num_v = float(m_exp.group())
                if any(m in str(raw_exp_explicit).lower() for m in ['month', 'mo', 'mos', 'mth']) and not any(y in str(raw_exp_explicit).lower() for y in ['year', 'yr', 'yrs']):
                    num_v = num_v / 12.0
                if num_v < 60.0:
                    exp_num = num_v
            except Exception:
                pass
    has_work_experience = (exp_num >= 1.0)

    # Check graduation year (<= 2025 is a completed past degree)
    grad_year_val = None
    grad_year_from_academic_org = False
    if prev_year and is_academic_org:
        m_yr = re.search(r'\b(19\d\d|20\d\d)\b', str(prev_year).replace(',', ''))
        if m_yr:
            grad_year_val = int(m_yr.group(1))          # at a college the year is the pass-out year
            grad_year_from_academic_org = True
    if not grad_year_val and raw_exp_explicit:
        m_yr_exp = re.search(r'\b(19\d\d|20\d\d)\b', str(raw_exp_explicit).replace(',', ''))
        if m_yr_exp:
            grad_year_val = int(m_yr_exp.group(1))

    has_past_graduation = (grad_year_val is not None and grad_year_val <= 2025)
    is_future_graduation = (grad_year_val is not None and grad_year_val >= 2026)

    is_role_explicitly_student = any(k in str(raw_role_explicit).lower() for k in ['student', 'intern', 'undergrad', 'learner', 'college'])

    # Strict Rule for Academic Emails (.edu / .ac.in / campus domains):
    # - If their graduation year is past (<= 2025) OR they work at a commercial company (or have >= 1 YOE):
    #   They are recognized as an Alumnus / Degree Holder -> Academic Status: Degree Verified (Eligible).
    # - If they have NO company, NO experience, and their graduation batch is future (2026+ or blank):
    #   Only then are they flagged as an Active College Student.
    if is_academic_email:
        if has_past_graduation or has_commercial_company or has_work_experience:
            is_detected_student = False if not is_role_explicitly_student else True
        else:
            is_detected_student = True
    elif is_academic_org:
        if has_commercial_company or has_work_experience or has_past_graduation:
            is_detected_student = False if not is_role_explicitly_student else True
        else:
            is_detected_student = True
    elif is_role_explicitly_student and not has_commercial_company and not has_work_experience:
        is_detected_student = True
    elif is_future_graduation and not has_commercial_company and not has_work_experience:
        is_detected_student = True
    else:
        is_detected_student = False

    if is_detected_student and not raw_role_explicit:
        raw_role = "College Student / Learner"
    else:
        raw_role = clean_str(raw_role_explicit, 'Prospective Learner' if is_detected_student else 'General Tech Professional')

    company_join_yr = None
    exp_is_explicit = False
    raw_exp_str = str(raw_exp_explicit).strip() if raw_exp_explicit is not None else ""
    if raw_exp_str.lower() in ['none', 'nan', 'null', '', '-']:
        raw_exp_str = ""

    if is_detected_student:
        if raw_exp_str:
            raw_exp = raw_exp_str if any(c.isdigit() for c in raw_exp_str) else f"{raw_exp_str}"
            exp_is_explicit = True
        else:
            raw_exp = "Fresher (College Student)"
            exp_is_explicit = False
    else:
        if raw_exp_str:
            if exp_num == 0.0 or raw_exp_str in ['0', '0.0', '0 yrs', '0 years', '0.0 years', '0.0 yrs']:
                if has_past_graduation and grad_year_val:
                    inferred_yoe = max(1, 2026 - grad_year_val)
                    raw_exp = f"{inferred_yoe} yrs (Batch {grad_year_val})"
                    exp_is_explicit = False
                elif prev_year and re.search(r'\b(19\d\d|20\d\d)\b', str(prev_year)):
                    # Company joining/tenure year
                    company_join_yr = int(re.search(r'\b(19\d\d|20\d\d)\b', str(prev_year)).group(1))
                    org_display = raw_org_clean if raw_org_clean and not is_empty_or_placeholder_org else "organization"
                    _now_yr = datetime.date.today().year
                    _tenure = max(1, _now_yr - company_join_yr) if 1990 <= company_join_yr <= _now_yr else None
                    if _tenure:
                        raw_exp = f"About {_tenure} yrs (With {org_display} since {company_join_yr})"
                        exp_num = float(_tenure)          # the years since joining count as work experience
                        has_work_experience = True
                    else:
                        raw_exp = f"0 yrs in role (With {org_display} since {company_join_yr})"
                        company_join_yr = None
                    exp_is_explicit = False
                elif has_commercial_company and not is_role_explicitly_student:
                    raw_exp = "Not Specified (Inferred 1-2 yrs)"
                    exp_is_explicit = False
                else:
                    raw_exp = "0 years (Fresher / Entry-Level)"
                    exp_is_explicit = True
            else:
                raw_exp = f"{raw_exp_str} years" if raw_exp_str.replace('.', '', 1).isdigit() else raw_exp_str
                exp_is_explicit = True
        else:
            exp_is_explicit = False
            if has_past_graduation and grad_year_val:
                inferred_yoe = max(1, 2026 - grad_year_val)
                raw_exp = f"{inferred_yoe} yrs (Batch {grad_year_val})"
            elif prev_year and re.search(r'\b(19\d\d|20\d\d)\b', str(prev_year)):
                company_join_yr = int(re.search(r'\b(19\d\d|20\d\d)\b', str(prev_year)).group(1))
                raw_exp = f"1-2 yrs baseline (Joined {company_join_yr})"
            else:
                raw_exp = "Not Specified (Inferred 1-2 yrs)"

    if is_detected_student and not raw_comp_explicit:
        company_type = "College / University Campus"
    else:
        company_type = clean_str(raw_comp_explicit, 'College Campus' if is_detected_student else 'IT Services / Technology')

    if is_detected_student and not raw_org_explicit:
        prev_org = email_domain.split('.')[0].upper() + " Campus" if is_academic_email else "College / University"
    else:
        prev_org = clean_str(raw_org_explicit, 'Current Organization')

    # Parse detailed academic credentials (UG vs PG, Entry Year, Expected Graduation Year)
    acad_info = parse_academic_credentials(email, raw_edu, prev_org, prev_year or (str(grad_year_val) if grad_year_val else ''))
    is_pg_student = acad_info['is_pg']
    expected_grad_year = acad_info['expected_grad_year'] or grad_year_val
    acad_status_text = acad_info['status_text']

    if is_detected_student:
        if expected_grad_year:
            prev_year = str(expected_grad_year)
        if is_pg_student:
            raw_role = "Postgraduate (Master's Student)" if not raw_role_explicit else raw_role
            raw_edu = "Master's Degree (PG Enrolled - Bachelor's Complete)" if not raw_edu or raw_edu in ['Graduated / Degree', 'Degree'] else raw_edu
        elif expected_grad_year:
            raw_role = f"College Student (Batch {expected_grad_year})" if not raw_role_explicit else raw_role

    # Normalized taxonomy & education
    persona = 'NON_TECH' if is_detected_student else normalize_persona('', raw_role)
    # A missing or generic role ('Other', 'General Professional') says nothing about the person. Use the other fields.
    from .role_taxonomy import classify_role
    _role_key, _role_why = classify_role(raw_role_explicit)
    from .role_taxonomy import normalize as _norm_role, PLACEHOLDERS as _ROLE_PLACEHOLDERS
    role_provided = _role_key is not None            # the role was recognised
    role_text_present = _norm_role(raw_role_explicit) not in _ROLE_PLACEHOLDERS   # something was written, recognised or not
    persona_inferred_from = None
    persona_basis = 'role' if role_provided else 'unknown'
    if role_provided and not is_detected_student:
        persona = _role_key
    elif not is_detected_student and not role_provided:
        # The role says nothing. Company type and program interest are weak but real signals (checked against learner data).
        _comp = str(raw_comp_explicit or '').lower()
        _interest = str(inbound_prog_raw or '').lower()
        if any(k in _comp for k in ('service', 'it ', 'technology', 'software', 'saas')) and 'non' not in _comp:
            persona, persona_inferred_from, persona_basis = 'IT_SERVICES', 'company type', 'inferred'
        elif 'product' in _comp and 'non' not in _comp:
            persona, persona_inferred_from, persona_basis = 'SWE_BACKEND', 'company type', 'inferred'
        elif re.search(r'devops|fde|forward deployed|ai\s*(and|&|/)?\s*ml|agentic', _interest):
            persona, persona_inferred_from, persona_basis = 'IT_SERVICES', 'program interest', 'inferred'
        else:
            persona = 'NON_TECH'
    persona_name = ('Postgraduate / Master\'s Student' if is_pg_student else 'Student / College Fresher') if is_detected_student else get_canonical_persona_name(persona)
    role_domain = 'Early Career & College Transitions' if is_detected_student else classify_world_domain(raw_role)
    if not is_detected_student and persona != 'NON_TECH':
        role_domain = persona_name   # keep the domain consistent with the persona
    if is_detected_student:
        exp_bracket = 'EXP_0_1'
    elif not exp_is_explicit:
        if has_past_graduation and grad_year_val:
            exp_bracket = normalize_experience(str(max(1, 2026 - grad_year_val)))
        elif company_join_yr:
            exp_bracket = normalize_experience(str(max(1, datetime.date.today().year - company_join_yr)))   # at least the years since joining the last organisation
        elif any(k in raw_role.lower() for k in ['leadership', 'director', 'vp', 'head of', 'architect', 'principal']):
            exp_bracket = 'EXP_5_PLUS'
        else:
            exp_bracket = 'EXP_1_3'
    else:
        exp_bracket = normalize_experience(raw_exp)
    # Only a graduation year is known: correct the years-since-graduation estimate with what enrolled learners really reported
    _grad_m = re.search(r'\((?:Batch|since|With[^)]*?since)\s*(\d{4})\)', str(raw_exp))
    if _grad_m and not is_detected_student:
        from .experience_model import predict_band
        _band = predict_band(datetime.date.today().year - int(_grad_m.group(1)), is_empty_or_placeholder_org, raw_comp_explicit, inbound_prog_raw, not role_provided)
        if _band:
            exp_bracket = _band
    edu_level = classify_education(raw_edu)
    inbound_str = str(inbound_prog_raw).lower().replace('_', ' ').replace('-', ' ')
    # Education: use the source value; if it is missing, infer graduation from other fields (a working professional has graduated)
    edu_given = bool(_field(['education', 'degree', 'qualification', 'highest_qualification', 'stream'])) and not lead_dict.get('education_missing')
    edu_inferred_from = None
    if not edu_given and not is_detected_student:
        _now_yr = datetime.date.today().year
        if has_past_graduation and grad_year_val:
            edu_inferred_from = (f"graduation year {grad_year_val}" if grad_year_from_academic_org else f"working since {grad_year_val}")
        elif exp_num and exp_num > 0:
            edu_inferred_from = f"about {round(exp_num, 1):g} yrs of work experience"
        elif company_join_yr and 1990 <= company_join_yr <= _now_yr:
            edu_inferred_from = f"working since {company_join_yr}"
        elif has_commercial_company:
            edu_inferred_from = "employment at a company"
    education_basis = 'source' if edu_given else ('inferred' if edu_inferred_from else 'assumed')
    edu_assumed = (education_basis == 'assumed')

    
    # =========================================================================
    # ACADEMIC ELIGIBILITY GATE: BELOW GRADUATION OR INCOMPLETE COLLEGE DEGREE
    # Strict Rule: Candidate MUST have completed graduation to be eligible for any Scaler course.
    # PG Master's students are eligible because they already hold a completed Bachelor's degree.
    # =========================================================================
    is_undergrad_incomplete = (is_detected_student and not is_pg_student and (expected_grad_year is None or expected_grad_year >= 2026))

    if edu_level == 'BELOW_GRAD' or is_undergrad_incomplete:
        first_name = name.split()[0] if name else 'there'
        if is_undergrad_incomplete:
            prim_why = (
                f"Candidate is an undergraduate college student ({prev_org}"
                f"{f', Batch {expected_grad_year}' if expected_grad_year else ''}) who has not completed graduation. "
                "All Scaler programs strictly mandate a completed undergraduate Bachelor's degree prior to enrollment. "
                "Candidates currently enrolled in college are not eligible for any Scaler career course until formal graduation."
            )
            guardrail_text = "Hard Academic Gate: Mandatory Bachelor degree completion required prior to enrollment in any Scaler course."
            status_badge_text = f"Ineligible (College Student - Degree Incomplete{f' Batch {expected_grad_year}' if expected_grad_year else ''})"
            pitch_text = (
                f'"Hi {first_name}, thank you for your interest in Scaler. Based on your profile, you are currently an undergraduate college student at {prev_org}. '
                'At Scaler, all our career programs strictly require candidates to have formally completed their Bachelor\'s degree prior to enrollment. '
                'Because companies and our curriculum mandate complete graduation, college students are not eligible to enroll in any Scaler courses until they graduate."'
            )
            inbound_handle_text = '"We encourage you to focus fully on completing your college semester academics and GPA. Once you complete your graduation, we will be delighted to welcome you into our cohorts."'
        else:
            prim_why = (
                f"Candidate's education background ({raw_edu}) does not satisfy Scaler's formal graduation prerequisite. "
                "All Scaler career programs strictly mandate a completed undergraduate Bachelor's degree. "
                "Enrolling without graduation is not permitted."
            )
            guardrail_text = "Hard Academic Gate: Mandatory Bachelor degree completion required prior to enrollment in any Scaler course."
            status_badge_text = "Ineligible (Degree Prerequisite)"
            pitch_text = (
                f'"Hi {first_name}, thank you for connecting with Scaler. I reviewed your profile and noticed your education background is {raw_edu}. '
                'At Scaler, all our programs strictly require learners to hold an undergraduate Bachelor\'s degree. '
                'Because companies enforce strict degree cutoffs in technical hiring rounds, candidates without a Bachelor\'s degree are not eligible to enroll in any Scaler course."'
            )
            inbound_handle_text = '"Our honest recommendation is to first complete a formal degree program (such as a BCA, B.Sc, or B.Tech). Upon completion of your degree, we will gladly fast-track your enrollment into our technical cohorts."'

        prim = {
            'program': 'Not Eligible (Degree Completion Prerequisite)',
            'catalog_code': 'Academic Prerequisite Gate',
            'track': 'Academic Eligibility Prerequisite',
            'fit_tier': 'Ineligible for Enrollment',
            'why': prim_why,
            'guardrail': guardrail_text,
            'duration': 'N/A',
            'retention_rate': 0.0,
            'refund_rate': 100.0,
            'cohort_size': 0,
            'risk_tag': 'Ineligible',
            'confidence_tier': 'Low',
            'confidence_score': 0,
            'confidence_rationale': 'Ineligible: Mandatory Bachelor degree completion required for all Scaler courses.',
            'confidence_breakdown': {
                'cohort_pts': 0, 'cohort_max': 35, 'cohort_desc': 'Ineligible',
                'ret_pts': 0, 'ret_max': 25, 'ret_desc': 'Ineligible',
                'intent_pts': 0, 'intent_max': 25, 'intent_desc': 'Ineligible',
                'apt_pts': 0, 'apt_max': 15, 'apt_desc': 'Degree completion prerequisite unfulfilled'
            }
        }
        fall = {
            'program': 'Degree Completion Pathway / College Academic Focus',
            'catalog_code': 'Academic Prerequisite Pathway',
            'track': 'Degree Completion Route',
            'fit_tier': 'Preparatory Route',
            'why': "Advise candidate to complete their college graduation first before applying to Scaler career accelerators.",
            'guardrail': 'Academic counseling path',
            'duration': f"{max(1, (expected_grad_year - 2026))} Year(s)" if expected_grad_year and expected_grad_year > 2026 else "Until Graduation",
            'retention_rate': 0.0,
            'refund_rate': 0.0,
            'cohort_size': 0,
            'risk_tag': 'Prerequisite Needed',
            'confidence_tier': 'Low',
            'confidence_score': 0,
            'confidence_rationale': 'Academic counseling pathway.',
            'confidence_breakdown': {
                'cohort_pts': 0, 'cohort_max': 35, 'cohort_desc': 'Ineligible',
                'ret_pts': 0, 'ret_max': 25, 'ret_desc': 'Ineligible',
                'intent_pts': 0, 'intent_max': 25, 'intent_desc': 'Ineligible',
                'apt_pts': 0, 'apt_max': 15, 'apt_desc': 'College degree completion required'
            }
        }
        sales_script = {
            'call_opening': f'"Hi {first_name}, thank you for reaching out to Scaler. I reviewed your academic profile and see you are currently {raw_role} at {prev_org}."',
            'program_pitch': pitch_text,
            'inbound_handling': inbound_handle_text
        }
        return {
            'person': {
                'name': name, 'email': email, 'phone': phone, 'role': raw_role,
                'role_domain': role_domain,
                'company_type': company_type, 'previous_org': prev_org, 'previous_org_year': prev_year,
                'experience': raw_exp, 'enquired_program': inbound_prog_raw,
                'education': raw_edu, 'education_level': edu_level,
                'sat_score': raw_sat_score, 'sat_status': raw_sat_status,
                'set_score': raw_sat_score, 'set_status': raw_sat_status,
                'normalized_persona': persona_name, 'persona_key': persona, 'normalized_experience': exp_bracket
            },
            'primary': prim,
            'fallback': fall,
            'sales_script': sales_script,
            'academic_eligibility': {
                'status': status_badge_text,
                'is_eligible': False,
                'degree_tier': acad_info['degree_tier'],
                'is_pg': is_pg_student,
                'expected_grad_year': expected_grad_year,
                'batch_label': acad_info['batch_label'],
                'rationale': f"Education status: {status_badge_text}. Formal Bachelor's degree completion is mandatory for enrollment in all Scaler courses."
            }
        }

    # Detect inbound program category
    inbound_stated = inbound_given
    if re.search(r'\b(program\s*3|p3|prog\s*3|fde|forward deployed|solutions engineer)\b', inbound_str):
        inbound_cat = 'P3_FDE'
    elif re.search(r'\b(program\s*4|p4|prog\s*4|agentic|aiml|ai\s?ml|ai\s*(and|&|/|-)\s*ml|artificial intelligence|deep learning|llm|genai|gen ai|generative ai|ai agent)\b', inbound_str):
        inbound_cat = 'P4_AIML_AGENTIC'
    elif re.search(r'\b(program\s*2|p2|prog\s*2|dsml|data\s?science|data analytics|analytics|data engineer)\b', inbound_str) or 'machine learning' in inbound_str:
        inbound_cat = 'P2_DSML'
    elif re.search(r'\b(program\s*5|p5|prog\s*5|devops|cloud|platform|sre|kubernetes|docker)\b', inbound_str):
        inbound_cat = 'P5_DEVOPS_CLOUD'
    else:
        inbound_cat = 'P1_ACADEMY'
        inbound_stated = inbound_given and bool(re.search(r'\b(program\s*1|p1|prog\s*1|academy|software|full\s?stack|sde)\b', inbound_str))
    conf_inbound_cat = inbound_cat   # the lead's real enquiry, used for the confidence score

    # 1. Allowlist for Tech Roles
    tech_keywords = [
        'sde', 'swe', 'software', 'developer', 'frontend', 'backend', 'full stack', 'fullstack', 'programmer',
        'devops', 'cloud', 'sre', 'sysadmin', 'infrastructure', 'platform engineer',
        'data', 'analytics', 'analyst', 'bi', 'machine learning', 'ml', 'ai', 'artificial intelligence',
        'qa', 'sdet', 'testing', 'automation', 'embedded', 'firmware', 'linux kernel', 'architect',
        'systems engineer', 'system engineer', 'systems', 'system', 'hardware', 'vlsi', 'network engineer',
        'cyber security', 'cybersecurity', 'security engineer', 'dba', 'database administrator', 'solutions engineer', 'fde',
        'engineering manager', 'tech lead', 'technical lead', 'lead architect', 'software architect',
        'solutions architect', 'enterprise architect', 'cto', 'vp of engineering', 'director of engineering',
        'ui engineer', 'web engineer', 'mobile engineer', 'device driver', 'appsec', 'build and release',
        'release engineer', 'computer vision', 'nlp', 'applied scientist', 'big data', 'etl'
    ]
    is_tech = (
        persona in ['SYSTEMS_ENG', 'DEVOPS_CLOUD', 'DATA_ANALYST', 'QA_SDET', 'SWE_BACKEND', 'FRONTEND', 'LEADERSHIP', 'IT_SERVICES'] or
        any(match_token(raw_role.lower(), k) for k in tech_keywords) or
        (match_token(raw_role.lower(), 'team lead') and not any(op in raw_role.lower() for op in [
            'operation', 'bpo', 'kpo', 'support', 'sales', 'marketing', 'hr', 'talent',
            'retail', 'logistics', 'finance', 'non-tech', 'call center', 'process'
        ]))
    )
    # Exclude non-software engineering domains (unless explicitly classified as tech)
    if persona == 'NON_TECH':
        is_tech = False

    is_career_break = any(k in raw_role.lower() for k in ['career break', 'break', 'sabbatical', 'gap', 'gap year', 'returning', 'homemaker', 'restart'])
    is_role_explicitly_student = any(k in raw_role.lower() for k in ['student', 'intern', 'undergrad', 'learner', 'college'])
    if has_commercial_company and is_tech and not is_role_explicitly_student:
        is_student = False
    else:
        is_student = is_detected_student or is_role_explicitly_student or (
            (exp_bracket == 'EXP_0_1') and not has_commercial_company and not has_work_experience and not has_past_graduation
        )

    is_non_tech = (
        is_career_break or 
        (edu_level == 'GRAD_NON_CS' and is_student) or 
        (persona in ['NON_TECH', 'Non-Tech / Operations', 'Non-Tech / Career Switcher']) or 
        not is_tech
    )

    is_qa = (not is_non_tech) and (persona in ['QA_SDET', 'QA / SDET / Testing'] or any(k in raw_role.lower() for k in ['test', 'qa', 'sdet', 'automation']))
    is_data = (not is_non_tech) and (persona in ['DATA_ANALYST', 'Data & Analytics'] or any(k in raw_role.lower() for k in ['data', 'analyst', 'analytics', 'bi ']))
    is_systems = (not is_non_tech) and (persona in ['SYSTEMS_ENG', 'Systems & Embedded Engineering'] or any(k in raw_role.lower() for k in ['system', 'embedded', 'linux', 'hardware']))
    is_devops = (not is_non_tech) and (
        persona in ['DEVOPS_CLOUD', 'DevOps & Cloud Platform'] or
        any(k in raw_role.lower() for k in ['devops', 'cloud', 'sre', 'platform engineer', 'sysadmin', 'system admin', 'infrastructure', 'kubernetes', 'docker', 'terraform', 'site reliability'])
    )
    is_senior = (not is_student) and (not is_non_tech) and (
        exp_bracket in ['EXP_5_PLUS', '5-8 years', '8+ years', '5+ yrs (Senior / Lead)'] or 
        (exp_bracket == 'EXP_3_5' and any(k in raw_role.lower() for k in ['lead', 'senior', 'manager', 'leadership', 'director', 'founder', 'architect', 'vp'])) or
        (any(k in raw_role.lower() for k in ['leadership', 'director', 'vp', 'head of', 'architect', 'principal']) and has_commercial_company)
    )

    # 3. FDE eligibility from the FDE brochure: engineering / IT / maths background and at least 1 year of coding (backend rule, not shown on cards)
    is_eligible_for_fde = (not is_non_tech) and (exp_bracket in ['EXP_1_3', 'EXP_3_5', 'EXP_5_PLUS'])

    # No program interest stated: the lead's persona decides the starting program (not a blanket default to Program 1)
    if not inbound_stated and not is_non_tech:
        if is_data:
            inbound_cat = 'P2_DSML'
        elif is_devops or is_systems:
            inbound_cat = 'P5_DEVOPS_CLOUD'
    elif (is_devops or is_systems) and inbound_cat == 'P1_ACADEMY':
        # a DevOps or systems persona gets the platform program first even when the generic Academy enquiry was stated
        inbound_cat = 'P5_DEVOPS_CLOUD'

    if force_inbound:
        inbound_cat = force_inbound   # used by the program ranking to build the card for a specific program

    primary = {}
    fallback = {}

    # =========================================================================
    # SCENARIO 1: NON-TECH / ZERO-CODE (Strict Catalog Gate)
    # =========================================================================
    if is_non_tech:
        # Check if the candidate's domain is Commercial / Business Management / People / Finance / Product Management
        is_product_manager = any(k in raw_role.lower() for k in ['product manager', 'associate product manager', 'apm', 'tpm', 'product owner', 'scrum master'])
        is_commercial_business = (
            any(d in role_domain for d in ['Marketing', 'Commerce', 'Finance', 'HR & People', 'Sales', 'Business Operations', 'Product Management & Design']) or
            is_product_manager or
            any(k in raw_role.lower() for k in [
                'marketing', 'brand', 'growth', 'category', 'merchandis', 'pricing', 'e-commerce', 'ecommerce',
                'finance', 'account', 'ca ', 'cpa', 'auditor', 'banking', 'bank officer', 'loan officer',
                'hr', 'human resource', 'people ops', 'recruiter', 'talent', 'sales', 'bde', 'bda',
                'business development', 'operations manager', 'supply chain', 'logistics',
                'team lead - operations', 'team lead operations', 'operations team lead', 'operations lead',
                'operations supervisor', 'process associate', 'process lead', 'project coordinator'
            ])
        )

        # Case 1: Inbound enquiry is directly DSML (or candidate is in commercial/business/product domain and enquired about advanced infrastructure/AI)
        if inbound_cat == 'P2_DSML' or (is_commercial_business and inbound_cat in ['P5_DEVOPS_CLOUD', 'P3_FDE', 'P4_AIML_AGENTIC']):
            primary['program'] = 'Modern Data Science & Machine Learning (DSML)'
            primary['catalog_code'] = 'Program 2'
            primary['track'] = 'Beginner Track (Data Analytics, Python & Business ML)'
            primary['fit_tier'] = 'Best Fit (Applied AI & Product Analytics)' if is_product_manager else 'Best Fit (Applied Business & Growth Analytics)'
            
            if inbound_cat == 'P5_DEVOPS_CLOUD':
                primary['why'] = (
                    f"While you enquired about DevOps & Cloud Platform, Program 5 strictly requires existing operating systems, "
                    f"networking, and Linux infrastructure foundations. With {raw_exp} as a {raw_role}, your suggested upskilling path is "
                    " Program 2: Modern Data Science & Machine Learning. Rather than wrestling with "
                    "cloud infrastructure automation from scratch, this track directly empowers your commercial leadership with SQL data pipelines, "
                    "growth analytics dashboards, and predictive machine learning models."
                )
                primary['guardrail'] = "Catalog Gate: Commercial professional redirected from DevOps/Kubernetes to high-retention DSML track."
            elif inbound_cat == 'P3_FDE':
                primary['why'] = (
                    f"While you showed high interest in Forward Deployed Engineering, Program 3 requires hands-on software "
                    f"deployment depth. As a {raw_role} with {raw_exp}, Program 2 equips you with data querying, Python analytics, "
                    "and predictive modeling to build technical data capability natively within your business domain."
                )
                primary['guardrail'] = "Catalog Gate: Redirected from FDE client systems to DSML beginner track."
            elif inbound_cat == 'P4_AIML_AGENTIC':
                if is_product_manager:
                    primary['why'] = (
                        f"While you enquired about Agentic AI, building production autonomous agents mandates data querying and predictive modeling foundations. "
                        f"As a {raw_role} with {raw_exp}, Program 2 directly empowers your product leadership with SQL data extraction, "
                        "product experimentation metrics, and applied machine learning models to design, evaluate, and productize AI systems without "
                        "getting bogged down in low-level compiler syntax drills."
                    )
                    primary['guardrail'] = "Catalog Gate: Product leader routed to applied analytics & ML before autonomous agent deployment."
                else:
                    primary['why'] = (
                        f"While you enquired about Frontier Agentic AI, building production autonomous agents mandates coding foundations. "
                        f"As a {raw_role} with {raw_exp}, Program 2 provides a high-retention onramp starting with data analytics, "
                        "applied machine learning, and business intelligence."
                    )
                    primary['guardrail'] = "Catalog Gate: Foundation in data & ML required before autonomous agent design."
            else:
                primary['why'] = (
                    f"With your background as a {raw_role}, Data Science & Analytics offers the smoothest, "
                    "path into tech. Rather than wrestling with abstract software architecture, "
                    "this track leverages your business domain experience into People/Business Analytics, SQL dashboards, "
                    "and applied Predictive Machine Learning from ground zero."
                )
                primary['guardrail'] = "Catalog Fit: Non-tech professional routed to DSML Beginner Track to build data fundamentals."

            fallback['program'] = 'Software & AI Engineering (Scaler Academy)'
            fallback['catalog_code'] = 'Program 1'
            fallback['track'] = 'Beginner Track (Foundations of Programming & Problem Solving)'
            fallback['fit_tier'] = 'Alternative Core Software Path'
            fallback['why'] = (
                "If you wish to pivot into core application software engineering rather than data analytics, "
                "Scaler Academy's Beginner Track teaches programming syntax, logic building, and problem solving from scratch."
            )
        else:
            primary['program'] = 'Software & AI Engineering (Scaler Academy)'
            primary['catalog_code'] = 'Program 1'
            primary['track'] = 'Beginner Track (Foundations of Programming & Problem Solving)'
            primary['fit_tier'] = 'Best Fit (Foundational Bridge)'
            if is_career_break:
                primary['why'] = (
                    f"For candidates returning to the industry after a career break, Scaler Academy's Beginner Track "
                    "provides a structured, supportive ramp-up covering syntax, modern developer tooling, and algorithmic logic from ground zero."
                )
            elif edu_level == 'GRAD_NON_CS':
                primary['why'] = (
                    f"With a non-computer science degree ({raw_edu}), the Beginner Track ensures you build systematic "
                    "problem-solving and coding foundations before tackling advanced data structures and system design."
                )
            else:
                primary['why'] = (
                    f"As a {raw_role} without professional coding exposure, Scaler Academy's Beginner Track "
                    "starts from ground zero (syntax, logic, loops, conditional branching). "
                    "It builds the prerequisite programming foundation before advancing to algorithms."
                )
            primary['guardrail'] = "Strict Negative Filter: Blocked from Intermediate/Advanced tracks to prevent Day 14 pacing dropout."

            if inbound_cat in ['P4_AIML_AGENTIC', 'P3_FDE']:
                fallback['program'] = 'AI & Machine Learning with Agentic AI'
                fallback['catalog_code'] = 'Program 4'
                fallback['track'] = 'Beginner Track (AI & Machine Learning Foundations)'
                fallback['fit_tier'] = 'High Risk / Conditional Fallback'
                fallback['why'] = (
                    f"You enquired about AI, but Catalog Rule 6 strictly mandates coding aptitude. "
                    "Non-tech learners are better served by a program that starts with programming basics."
                )
            elif inbound_cat == 'P5_DEVOPS_CLOUD':
                fallback['program'] = 'Modern Data Science & Machine Learning (DSML)'
                fallback['catalog_code'] = 'Program 2'
                fallback['track'] = 'Beginner Track (Data Analytics Foundation)'
                fallback['fit_tier'] = 'Alternative Analytics Path'
                fallback['why'] = (
                    "While you enquired about DevOps, cloud infrastructure requires deep Linux and networking fundamentals. "
                    "DSML offers a high-retention data analytics alternative."
                )
            else:
                fallback['program'] = 'Modern Data Science & Machine Learning (DSML)'
                fallback['catalog_code'] = 'Program 2'
                fallback['track'] = 'Beginner Track (Data Analytics Foundation)'
                fallback['fit_tier'] = 'Alternative Analytics Path'
                fallback['why'] = "Provides an alternative route into tech through business intelligence, SQL, and data reporting."

    # =========================================================================
    # SCENARIO 2: DATA & ANALYTICS ROLES (Data Analyst, BI, SQL Dev)
    # =========================================================================
    elif is_data:
        if inbound_cat == 'P4_AIML_AGENTIC':
            if is_student:
                primary['program'] = 'AI & Machine Learning with Agentic AI'
                primary['catalog_code'] = 'Program 4'
                primary['track'] = 'Beginner Track (AI & Machine Learning Foundations)'
                primary['fit_tier'] = 'Best Fit (Foundational AI & Agentic Systems)'
                primary['why'] = (
                    f"As an early-career learner aiming for AI & ML, Program 4's Beginner Track builds your foundation "
                    "with Python programming and applied math, before advancing into neural networks and autonomous agent systems."
                )
                primary['guardrail'] = "Early Career / Fresher: Routed to Beginner Track (AI & ML Foundations) with structured Python onramp."

                fallback['program'] = 'Modern Data Science & Machine Learning (DSML)'
                fallback['catalog_code'] = 'Program 2'
                fallback['track'] = 'Beginner Track (Data Analytics, Python & Business ML)'
                fallback['fit_tier'] = 'Alternative Foundation Analytics Track'
                fallback['why'] = "A safer, high-retention foundational path focusing on Python data analytics, statistical modeling, and business ML."
            else:
                primary['program'] = 'AI & Machine Learning with Agentic AI'
                primary['catalog_code'] = 'Program 4'
                primary['track'] = 'Advanced Track (Agentic AI & LLMOps)'
                primary['fit_tier'] = 'Best Fit (Advanced AI Modeling)'
                primary['why'] = (
                    f"Your background as a {raw_role} gives you data intuition. Program 4 elevates you into "
                    "deep learning, neural networks, PyTorch, and building multi-agent autonomous AI systems."
                )
                primary['guardrail'] = "Catalog Tie-Breaker: Routed to Program 4 due to explicit intent to build/deploy AI models."
                
                fallback['program'] = 'Modern Data Science & Machine Learning (DSML)'
                fallback['catalog_code'] = 'Program 2'
                fallback['track'] = 'Core Analytics & Predictive Modeling Track'
                fallback['fit_tier'] = 'Alternative Analytics Specialization'
                fallback['why'] = "A safer, high-retention path focusing on predictive analytics, statistical hypothesis testing, and business ML."
        elif inbound_cat == 'P1_ACADEMY':
            primary['program'] = 'Modern Data Science & Machine Learning (DSML)'
            primary['catalog_code'] = 'Program 2'
            primary['track'] = 'Core Analytics & Machine Learning Track'
            primary['fit_tier'] = 'Best Fit (Domain Native)'
            primary['why'] = (
                f"Your background as a {raw_role} directly leverages SQL and business data into predictive machine learning."
            )
            primary['guardrail'] = "Catalog Rule: Native fit in Program 2; Academy offered as bridge for software pivot."

            fallback['program'] = 'Software & AI Engineering (Scaler Academy)'
            fallback['catalog_code'] = 'Program 1'
            fallback['track'] = 'Data Engineering & Backend Systems Track'
            fallback['fit_tier'] = 'Inbound Software Career Pivot'
            fallback['why'] = (
                "Since you enquired about Academy, this track bridges your SQL foundation into large-scale Data Engineering, "
                "distributed pipelines (Spark/Kafka), and backend API architecture."
            )
        elif inbound_cat == 'P3_FDE':
            if is_eligible_for_fde and any(k in raw_role.lower() for k in ['data engineer', 'pipeline', 'senior', 'lead', 'architect']):
                primary['program'] = 'AI Forward Deployed Engineer (FDE)'
                primary['catalog_code'] = 'Program 3'
                primary['track'] = 'Enterprise AI Integration & Production RAG Track'
                primary['fit_tier'] = 'Best Fit (Data Pipeline & Client AI Integration)'
                primary['why'] = (
                    f"As a {raw_role} with {raw_exp}, your data pipeline, PySpark, and database foundations translate directly "
                    "into Program 3's core mission: client enterprise ingestion pipelines, production RAG architectures, and live AI deployment."
                )
                primary['guardrail'] = "Verified data engineering background matches FDE client integration requirements."

                fallback['program'] = 'Modern Data Science & Machine Learning (DSML)'
                fallback['catalog_code'] = 'Program 2'
                fallback['track'] = 'Core Analytics & Machine Learning Track'
                fallback['fit_tier'] = 'Alternative Core Analytics Track'
                fallback['why'] = "Deep statistical modeling and predictive machine learning alternative."
            else:
                primary['program'] = 'Modern Data Science & Machine Learning (DSML)'
                primary['catalog_code'] = 'Program 2'
                primary['track'] = 'Core Analytics & Machine Learning Track'
                primary['fit_tier'] = 'Best Fit (Domain Native Foundation)'
                primary['why'] = (
                    f"While you enquired about FDE, Program 3 requires production deployment depth. "
                    "Program 2 builds your predictive modeling, advanced analytics, and data pipeline fundamentals first."
                )
                primary['guardrail'] = "Catalog Gate: Data professionals routed to DSML core track before client-facing AI deployment."

                fallback['program'] = 'AI Forward Deployed Engineer (FDE)'
                fallback['catalog_code'] = 'Program 3'
                fallback['track'] = 'Enterprise AI Integration Track'
                fallback['fit_tier'] = 'Aspirational Goal (Post-Analytics)'
                fallback['why'] = "Target program once production data pipelines and machine learning workflows are mastered."
        elif inbound_cat == 'P5_DEVOPS_CLOUD':
            is_data_engineer = any(k in raw_role.lower() for k in ['data engineer', 'big data', 'etl', 'pipeline', 'database engineer'])
            is_pure_analyst = any(k in raw_role.lower() for k in ['data analyst', 'bi analyst', 'business analyst', 'analytics consultant', 'tableau', 'power bi']) and not is_data_engineer
            
            if is_pure_analyst:
                primary['program'] = 'Modern Data Science & Machine Learning (DSML)'
                primary['catalog_code'] = 'Program 2'
                primary['track'] = 'Core Analytics & Machine Learning Track' if not is_student else 'Beginner Track (Data Analytics, Python & Business ML)'
                primary['fit_tier'] = 'Best Fit (Domain Native Specialization)'
                primary['why'] = (
                    f"While you enquired about DevOps & Cloud Platform, Program 5 strictly requires operating systems, bash/Linux scripting, networking, "
                    f"and server administration foundations. As a {raw_role} with {raw_exp}, your suggested career progression "
                    "is Program 2: Modern Data Science & Machine Learning. This track directly builds upon your existing SQL and analytical strengths into "
                    "predictive modeling, machine learning, and scalable data engineering. Cloud platform engineering remains an aspirational future specialisation "
                    "once infrastructure fundamentals are established."
                )
                primary['guardrail'] = "Catalog Gate: Data Analyst redirected to DSML; Linux/OS prerequisites required before SRE/Kubernetes."

                fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
                fallback['catalog_code'] = 'Program 5'
                fallback['track'] = 'CI/CD Automation & Cloud Infrastructure Track'
                fallback['fit_tier'] = 'Aspirational Infrastructure Pivot'
                fallback['why'] = "Secondary path if you intend to transition into DataOps and cloud infrastructure, starting with foundational Linux & CI/CD."
            else:
                primary['program'] = 'DevOps, Cloud & AI Platform Engineering'
                primary['catalog_code'] = 'Program 5'
                primary['track'] = 'Site Reliability Engineering (SRE) & Kubernetes Track' if is_senior else 'CI/CD Automation & Cloud Infrastructure Track'
                primary['fit_tier'] = 'Best Fit (DataOps & Cloud Infrastructure)'
                primary['why'] = (
                    f"Your background as a {raw_role} connects naturally into DataOps and cloud platform engineering - "
                    "managing distributed data pipelines, cloud databases, and Kubernetes clusters."
                )
                primary['guardrail'] = "Natural transition from data handling to cloud infrastructure and DataOps."

                fallback['program'] = 'Modern Data Science & Machine Learning (DSML)'
                fallback['catalog_code'] = 'Program 2'
                fallback['track'] = 'Core Analytics & Machine Learning Track'
                fallback['fit_tier'] = 'Alternative Domain Native Track'
                fallback['why'] = "Core statistical modeling and machine learning alternative."
        else:
            primary['program'] = 'Modern Data Science & Machine Learning (DSML)'
            primary['catalog_code'] = 'Program 2'
            primary['track'] = 'Core Analytics & Machine Learning Track'
            primary['fit_tier'] = 'Best Fit (Domain Native)'
            primary['why'] = f"Directly accelerates your experience as a {raw_role} into statistical modeling and enterprise ML."
            primary['guardrail'] = "High retention cohort; verified quantitative aptitude."

            fallback['program'] = 'AI & Machine Learning with Agentic AI'
            fallback['catalog_code'] = 'Program 4'
            fallback['track'] = 'Advanced Track (Agentic AI & LLMOps)'
            fallback['fit_tier'] = 'Advanced Next-Gen AI Pivot'
            fallback['why'] = "Alternative path to specialize in frontier LLM engineering and agentic workflows."

    # =========================================================================
    # SCENARIO 3: QA / TEST AUTOMATION / SDET
    # =========================================================================
    elif is_qa:
        is_manual_qa = any(k in raw_role.lower() for k in ['manual', 'black box', 'functional test', 'test associate'])
        if inbound_cat == 'P5_DEVOPS_CLOUD':
            primary['program'] = 'DevOps, Cloud & AI Platform Engineering'
            primary['catalog_code'] = 'Program 5'
            primary['track'] = 'CI/CD Automation & Cloud Infrastructure Track'
            primary['fit_tier'] = 'Best Fit (Natural Synergistic Pivot)'
            primary['why'] = (
                f"Your testing background as a {raw_role} connects seamlessly into DevOps - "
                "expanding test validation suites into CI/CD pipelines, Docker containers, and Kubernetes orchestration."
            )
            primary['guardrail'] = "Catalog Tie-Breaker: Test skill naturally bridges to SRE & Cloud Engineering."

            fallback['program'] = 'Software & AI Engineering (Scaler Academy)'
            fallback['catalog_code'] = 'Program 1'
            fallback['track'] = 'Intermediate Track (Backend SDE Transition)'
            fallback['fit_tier'] = 'Alternative Core SDE'
            fallback['why'] = "If you prefer transitioning into core development, Academy focuses on Object-Oriented Design and DSA."
        elif inbound_cat == 'P2_DSML':
            primary['program'] = 'Modern Data Science & Machine Learning (DSML)'
            primary['catalog_code'] = 'Program 2'
            primary['track'] = 'Core Analytics & Machine Learning Track' if not is_student else 'Beginner Track (Data Analytics, Python & Business ML)'
            primary['fit_tier'] = 'Best Fit (Data Analytics & QA Synergy)'
            primary['why'] = (
                f"As a {raw_role}, your structured validation mindset and SQL test data verification directly empower "
                "data pipeline testing, exploratory data analysis, and predictive machine learning models."
            )
            primary['guardrail'] = "Verified quantitative transition track for quality assurance professionals."

            fallback['program'] = 'Software & AI Engineering (Scaler Academy)'
            fallback['catalog_code'] = 'Program 1'
            fallback['track'] = 'Intermediate Track (Backend SDE Transition)'
            fallback['fit_tier'] = 'Alternative Development Track'
            fallback['why'] = "Alternative path if you decide to pivot to core backend software engineering."
        elif inbound_cat == 'P3_FDE':
            primary['program'] = 'Software & AI Engineering (Scaler Academy)'
            primary['catalog_code'] = 'Program 1'
            primary['track'] = 'Intermediate Track (Backend SDE Transition)'
            primary['fit_tier'] = 'Foundational Prerequisite for FDE'
            primary['why'] = (
                f"While you enquired about Forward Deployed Engineering, Program 3 strictly mandates hands-on production backend development, "
                f"API deployment, and algorithmic problem-solving depth. With {raw_exp} in quality assurance & testing, jumping straight into "
                "client AI code deployment without modern backend development depth risks severe pacing friction. Scaler Academy's Intermediate Track "
                "(Backend SDE Transition) equips you with core algorithmic problem-solving, advanced data structures (DSA), low-level object-oriented "
                "design (LLD), and backend API architecture first, establishing the necessary engineering foundation before forward-deploying AI into enterprise environments."
            )
            primary['guardrail'] = "FDE Catalog Prerequisite: QA professionals require backend engineering, DSA & LLD foundations before client AI deployment."

            fallback['program'] = 'AI Forward Deployed Engineer (FDE)'
            fallback['catalog_code'] = 'Program 3'
            fallback['track'] = 'Enterprise AI Integration & Production RAG Track'
            fallback['fit_tier'] = 'Aspirational Goal (Post-Foundations)'
            fallback['why'] = (
                f"Target program once foundational backend software engineering, DSA, and object-oriented design are mastered, "
                f"leveraging your {raw_exp} of enterprise quality governance into live enterprise AI deployment."
            )

        elif inbound_cat == 'P4_AIML_AGENTIC':
            primary['program'] = 'AI & Machine Learning with Agentic AI'
            primary['catalog_code'] = 'Program 4'
            primary['track'] = 'Advanced Track (Agentic AI & LLMOps)' if is_senior else 'Beginner Track (AI & Machine Learning Foundations)'
            primary['fit_tier'] = 'Best Fit (AI Testing & Agentic Systems)'
            primary['why'] = (
                f"Leverages your test engineering precision as a {raw_role} to evaluate autonomous AI agents, "
                "build LLM verification benchmarks, and deploy agentic AI architectures."
            )
            primary['guardrail'] = "Pivots QA domain into next-generation AI evaluation and agent engineering."

            fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
            fallback['catalog_code'] = 'Program 5'
            fallback['track'] = 'CI/CD Automation & Cloud Infrastructure Track'
            fallback['fit_tier'] = 'Alternative Infrastructure Track'
            fallback['why'] = "Automates testing and AI agent deployment through modern cloud pipelines."
        else:
            is_pure_qa = any(k in raw_role.lower() for k in ['qa', 'test', 'quality']) and 'sdet' not in raw_role.lower()
            if is_manual_qa:
                primary['program'] = 'Software & AI Engineering (Scaler Academy)'
                primary['catalog_code'] = 'Program 1'
                if is_senior:
                    primary['track'] = 'Intermediate Track (Backend SDE Transition)'
                    primary['fit_tier'] = 'Best Fit (SDE Transition & Coding Foundation)'
                    primary['why'] = (
                        f"As a {raw_role} with {raw_exp}, you possess deep functional software domain knowledge and defect lifecycle mastery. "
                        "To successfully transition into engineering and automation roles, the critical gap is hands-on coding, data structures, "
                        "and low-level object-oriented design (LLD). This track bypasses generic high-level theory to focus directly on core "
                        "algorithmic problem-solving and clean code development."
                    )
                    primary['guardrail'] = "Manual QA Guardrail: Routed to Intermediate coding & LLD track; blocked from pure High-Level System Design until coding depth is established."
                else:
                    primary['track'] = 'Beginner Track (Foundations of Programming & Problem Solving)'
                    primary['fit_tier'] = 'Best Fit (Foundational Bridge)'
                    primary['why'] = (
                        f"As a {raw_role} with {raw_exp}, this Beginner Track teaches programming syntax, algorithmic logic, "
                        "and object-oriented development from ground zero to transition from manual testing into software engineering."
                    )
                    primary['guardrail'] = "Manual QA Guardrail: Routed to Beginner coding track to build algorithmic foundations."

                fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
                fallback['catalog_code'] = 'Program 5'
                fallback['track'] = 'CI/CD Automation & Cloud Infrastructure Track'
                fallback['fit_tier'] = 'Alternative Cloud Platform Path'
                fallback['why'] = "An alternative route to build automated deployment and cloud infrastructure skills."
            elif is_pure_qa:
                primary['program'] = 'Software & AI Engineering (Scaler Academy)'
                primary['catalog_code'] = 'Program 1'
                primary['track'] = 'Intermediate Track (Backend SDE Transition)'
                primary['fit_tier'] = 'Best Fit (Backend SDE Transition)'
                primary['why'] = (
                    f"As a {raw_role} with {raw_exp}, you already understand software lifecycles, release protocols, and code structures; "
                    "this track bridges the exact gap in algorithmic optimization, advanced DSA, and low-level object-oriented design (LLD) "
                    "to transition into core Backend SDE roles. Bypasses basic syntax to focus directly on Intermediate DSA (AI Assisted Problem Solving), "
                    "Advanced DSA (Divide & Conquer, Trees, Heaps, Graphs, Dynamic Programming), and Low-Level Design (LLD)."
                )
                primary['guardrail'] = "Calibrated for QA/Testing transition: Bridges DSA & LLD gaps to achieve product-company SDE readiness."

                fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
                fallback['catalog_code'] = 'Program 5'
                fallback['track'] = 'CI/CD Automation & Cloud Infrastructure Track' if not is_senior else 'Cloud Platform & Infrastructure Track'
                fallback['fit_tier'] = 'Alternative Cloud Platform Leadership' if is_senior else 'Alternative Infrastructure Path'
                fallback['why'] = "A fast-track alternative that leverages your testing automation into cloud engineering."
            elif is_senior:
                primary['program'] = 'Software & AI Engineering (Scaler Academy)'
                primary['catalog_code'] = 'Program 1'
                primary['track'] = 'Advanced Track (High-Level System Design & Scalability)'
                primary['fit_tier'] = 'Best Fit (Engineering Leadership & System Architecture)'
                primary['why'] = (
                    f"With {raw_exp} as a {raw_role}, you have mastered software delivery and test framework architecture. "
                    "This Advanced Track is for learners with notable coding experience: "
                    "distributed caching, database sharding, Kafka event streaming, and architectural scalability."
                )
                primary['guardrail'] = "Calibrated for senior technical leaders (5+ to 20+ YOE); skips junior DSA syntax."

                fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
                fallback['catalog_code'] = 'Program 5'
                fallback['track'] = 'Cloud Platform & Infrastructure Track'
                fallback['fit_tier'] = 'Alternative Cloud Platform Leadership'
                fallback['why'] = "A strategic alternative leveraging your quality and infrastructure background into enterprise cloud architecture."
            else:
                primary['program'] = 'Software & AI Engineering (Scaler Academy)'
                primary['catalog_code'] = 'Program 1'
                primary['track'] = 'Intermediate Track (Backend SDE Transition)'
                primary['fit_tier'] = 'Best Fit (Career Upgrade)'
                primary['why'] = (
                    f"Transitioning from {raw_role} to a product company SDE requires strengthening Data Structures "
                    "and Low-Level Design (LLD). Intermediate Track skips syntax basics to focus on interview-ready engineering."
                )
                primary['guardrail'] = "Calibrated for SDET/QA transition; provides systematic problem-solving."

                fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
                fallback['catalog_code'] = 'Program 5'
                fallback['track'] = 'CI/CD Automation & Cloud Infrastructure Track'
                fallback['fit_tier'] = 'Alternative Infrastructure Path'
                fallback['why'] = "A fast-track alternative that leverages your testing automation into cloud engineering."

    # =========================================================================
    # SCENARIO 4: SYSTEMS & EMBEDDED / HARDWARE / IT INFRASTRUCTURE
    # =========================================================================
    elif is_systems:
        if inbound_cat == 'P5_DEVOPS_CLOUD':
            primary['program'] = 'DevOps, Cloud & AI Platform Engineering'
            primary['catalog_code'] = 'Program 5'
            primary['track'] = 'Cloud Architecture & Linux Systems Track'
            primary['fit_tier'] = 'Best Fit (Direct OS/Hardware Synergy)'
            primary['why'] = (
                f"Your experience as a {raw_role} provides OS, networking, and memory fundamentals. "
                "DevOps modernizes this into cloud infrastructure, Terraform, and Kubernetes cluster operations."
            )
            primary['guardrail'] = "Catalog Rule: Strong historical retention cohort in Program 5."

            fallback['program'] = 'Software & AI Engineering (Scaler Academy)'
            fallback['catalog_code'] = 'Program 1'
            fallback['track'] = 'Intermediate Track (Core Software Engineering)'
            fallback['fit_tier'] = 'Alternative Product SDE'
            fallback['why'] = "If you want to pivot into application software, Academy teaches modern Java/C++ backend microservices."
        elif inbound_cat == 'P3_FDE':
            if is_eligible_for_fde:
                primary['program'] = 'AI Forward Deployed Engineer (FDE)'
                primary['catalog_code'] = 'Program 3'
                primary['track'] = 'Enterprise AI Integration & Client Systems Track'
                primary['fit_tier'] = 'Best Fit (Enterprise Systems Depth)'
                primary['why'] = (
                    f"Your low-level systems background fits Program 3's focus on deploying AI solutions live "
                    "inside enterprise environments, PySpark pipelines, and multi-agent enterprise infrastructure."
                )
                primary['guardrail'] = "Requires verified systems/backend foundation; passes prerequisite gate."

                fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
                fallback['catalog_code'] = 'Program 5'
                fallback['track'] = 'Site Reliability Engineering (SRE) & Kubernetes Track' if is_senior else 'CI/CD Automation & Cloud Infrastructure Track'
                fallback['fit_tier'] = 'Alternative Cloud Platform Leadership' if is_senior else 'Alternative Infrastructure Track'
                fallback['why'] = "Infrastructure alternative focusing on Kubernetes and platform scalability."
            else:
                primary['program'] = 'Software & AI Engineering (Scaler Academy)'
                primary['catalog_code'] = 'Program 1'
                primary['track'] = 'Intermediate Track (Java/C++ with DSA Core)'
                primary['fit_tier'] = 'Foundational Prerequisite for FDE'
                primary['why'] = (
                    f"While you showed high interest in Forward Deployed Engineering, Program 3 requires hands-on "
                    "production backend systems and deployment experience (2+ years). Scaler Academy bridges your systems foundation into production microservices first."
                )
                primary['guardrail'] = "Catalog Gate: FDE requires software deployment depth and 2+ YOE; learner routed to foundational track."

                fallback['program'] = 'AI Forward Deployed Engineer (FDE)'
                fallback['catalog_code'] = 'Program 3'
                fallback['track'] = 'Enterprise AI Integration Track'
                fallback['fit_tier'] = 'Aspirational Goal (Post-Foundations)'
                fallback['why'] = "Target program once foundational data structures and software engineering are mastered."
        elif inbound_cat == 'P2_DSML':
            primary['program'] = 'Modern Data Science & Machine Learning (DSML)'
            primary['catalog_code'] = 'Program 2'
            primary['track'] = 'Core Analytics & Machine Learning Track'
            primary['fit_tier'] = 'Best Fit (Quantitative Systems Synergy)'
            primary['why'] = (
                f"Your background as a {raw_role} provides low-level mathematical and algorithmic rigour. "
                "Program 2 leverages this into statistical modeling, high-throughput feature pipelines, and machine learning."
            )
            primary['guardrail'] = "Engineered for technical professionals pivoting to data and quantitative engineering."

            fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
            fallback['catalog_code'] = 'Program 5'
            fallback['track'] = 'Cloud Platform & Linux Track'
            fallback['fit_tier'] = 'Alternative Systems Infrastructure Path'
            fallback['why'] = "Alternative path building upon your OS and hardware background."
        elif inbound_cat == 'P4_AIML_AGENTIC':
            primary['program'] = 'AI & Machine Learning with Agentic AI'
            primary['catalog_code'] = 'Program 4'
            primary['track'] = 'Advanced Track (Agentic AI & LLMOps)' if not is_student else 'Beginner Track (AI & Machine Learning Foundations)'
            primary['fit_tier'] = 'Best Fit (Hardware-Accelerated AI & Agents)'
            primary['why'] = (
                f"Your systems foundation as a {raw_role} is ideal for GPU-accelerated computing, "
                "model quantization, edge AI deployment, and high-performance agentic pipelines."
            )
            primary['guardrail'] = "Matches hardware/systems depth with cutting-edge agentic architectures."

            fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
            fallback['catalog_code'] = 'Program 5'
            fallback['track'] = 'Cloud Platform & Linux Track'
            fallback['fit_tier'] = 'Alternative Systems Infrastructure Path'
            fallback['why'] = "Alternative path focusing on infrastructure scaling and platform resilience."
        else:
            if is_senior:
                primary['program'] = 'Software & AI Engineering (Scaler Academy)'
                primary['catalog_code'] = 'Program 1'
                primary['track'] = 'Advanced Track (High-Level System Design & Scalability)'
                primary['fit_tier'] = 'Best Fit (Senior Systems Architecture)'
                primary['why'] = (
                    f"With {raw_exp} in systems engineering as a {raw_role}, you already have deep OS and hardware fundamentals. "
                    "The Advanced Track elevates this into large-scale distributed architectures, database sharding, and high-level design."
                )
                primary['guardrail'] = "Senior track calibrated for experienced systems architects."
            else:
                primary['program'] = 'Software & AI Engineering (Scaler Academy)'
                primary['catalog_code'] = 'Program 1'
                primary['track'] = 'Intermediate Track (Java/C++ with DSA Core)'
                primary['fit_tier'] = 'Best Fit (Product Company Bridge)'
                primary['why'] = (
                    f"Engineers working as {raw_role} excel in Academy's Intermediate Track, "
                    "which bridges the gap between enterprise maintenance and Tier-1 product algorithmic standards."
                )
                primary['guardrail'] = "Calibrated for 2-5 YOE service engineers."

            fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
            fallback['catalog_code'] = 'Program 5'
            fallback['track'] = 'Cloud Platform & Linux Track'
            fallback['fit_tier'] = 'Alternative Systems Path'
            fallback['why'] = "Builds upon your OS and infrastructure background without requiring competitive algorithmic design."

    # =========================================================================
    # SCENARIO 5: DEVOPS, CLOUD, SRE & PLATFORM ENGINEERING
    # =========================================================================
    elif is_devops:
        if inbound_cat == 'P1_ACADEMY':
            primary['program'] = 'Software & AI Engineering (Scaler Academy)'
            primary['catalog_code'] = 'Program 1'
            primary['track'] = 'Advanced Track (High-Level System Design & Scalability)' if is_senior else 'Intermediate Track (Data Structures, Algorithms & LLD)'
            primary['fit_tier'] = 'Best Fit (Software Engineering Pivot)'
            primary['why'] = (
                f"As a {raw_role} with {raw_exp}, your infrastructure and deployment expertise is established. "
                "Scaler Academy adds algorithmic problem-solving and distributed backend microservices architecture to transition into full-stack product development."
            )
            primary['guardrail'] = "Calibrated for platform engineers pivoting into core application development."

            fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
            fallback['catalog_code'] = 'Program 5'
            fallback['track'] = 'Site Reliability Engineering (SRE) & Kubernetes Track'
            fallback['fit_tier'] = 'Alternative Domain Native Track'
            fallback['why'] = "Advanced cloud orchestration and platform leadership alternative."

        elif inbound_cat == 'P3_FDE':
            if is_eligible_for_fde:
                primary['program'] = 'AI Forward Deployed Engineer (FDE)'
                primary['catalog_code'] = 'Program 3'
                primary['track'] = 'Enterprise AI Integration & Production RAG Track'
                primary['fit_tier'] = 'Best Fit (Cloud-Native AI Deployment)'
                primary['why'] = (
                    f"Your background as a {raw_role} in Docker, Kubernetes, and cloud infrastructure directly bridges the "
                    "Enterprise Deployment Gap—containerizing autonomous AI agents and deploying RAG pipelines directly into customer cloud environments."
                )
                primary['guardrail'] = "Cloud and infrastructure expertise provides an ideal foundation for client-facing AI deployment."

                fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
                fallback['catalog_code'] = 'Program 5'
                fallback['track'] = 'Site Reliability Engineering (SRE) & Kubernetes Track'
                fallback['fit_tier'] = 'Alternative Cloud Platform Track'
                fallback['why'] = "Platform engineering and infrastructure automation alternative."
            else:
                primary['program'] = 'DevOps, Cloud & AI Platform Engineering'
                primary['catalog_code'] = 'Program 5'
                primary['track'] = 'CI/CD Automation & Cloud Infrastructure Track'
                primary['fit_tier'] = 'Foundational Cloud Prerequisite for FDE'
                primary['why'] = (
                    f"While you enquired about Forward Deployed Engineering, Program 3 requires established "
                    "production deployment experience (2+ years). Program 5 establishes your core containerization, CI/CD, and cloud infrastructure foundation first."
                )
                primary['guardrail'] = "Catalog Gate: FDE requires 2+ YOE in production deployment; learner routed to foundational cloud track."

                fallback['program'] = 'AI Forward Deployed Engineer (FDE)'
                fallback['catalog_code'] = 'Program 3'
                fallback['track'] = 'Enterprise AI Integration Track'
                fallback['fit_tier'] = 'Aspirational Goal (Post-Cloud Foundations)'
                fallback['why'] = "Target program once production containerization and cloud infrastructure are mastered."

        elif inbound_cat == 'P2_DSML':
            primary['program'] = 'Modern Data Science & Machine Learning (DSML)'
            primary['catalog_code'] = 'Program 2'
            primary['track'] = 'Core Analytics & Machine Learning Track' if not is_student else 'Beginner Track (Data Analytics, Python & Business ML)'
            primary['fit_tier'] = 'Best Fit (Cloud Infrastructure & MLOps Synergy)'
            primary['why'] = (
                f"As a {raw_role}, your cloud and infrastructure background provides an ideal foundation for MLOps, "
                "data pipeline orchestration, and deploying scalable machine learning models into production."
            )
            primary['guardrail'] = "Synergistic pivot from cloud platform engineering to data science and production ML."

            fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
            fallback['catalog_code'] = 'Program 5'
            fallback['track'] = 'Site Reliability Engineering (SRE) & Kubernetes Track' if is_senior else 'CI/CD Automation & Cloud Infrastructure Track'
            fallback['fit_tier'] = 'Alternative Cloud Platform Track'
            fallback['why'] = "Core infrastructure and Kubernetes platform engineering path."

        elif inbound_cat == 'P4_AIML_AGENTIC':
            primary['program'] = 'AI & Machine Learning with Agentic AI'
            primary['catalog_code'] = 'Program 4'
            primary['track'] = 'Advanced Track (Agentic AI & LLMOps)' if not is_student else 'Beginner Track (AI & Machine Learning Foundations)'
            primary['fit_tier'] = 'Best Fit (LLMOps & AI Infrastructure)'
            primary['why'] = (
                f"As a {raw_role}, your cloud background is a starting point for LLMOps, model serving "
                "and AI agent infrastructure."
            )
            primary['guardrail'] = "Synergistic pivot from cloud DevOps to LLMOps and AI infrastructure."

            fallback['program'] = 'DevOps, Cloud & AI Platform Engineering'
            fallback['catalog_code'] = 'Program 5'
            fallback['track'] = 'Site Reliability Engineering (SRE) & Kubernetes Track'
            fallback['fit_tier'] = 'Alternative Cloud Platform Track'
            fallback['why'] = "Core infrastructure and Kubernetes platform engineering path."

        else:
            primary['program'] = 'DevOps, Cloud & AI Platform Engineering'
            primary['catalog_code'] = 'Program 5'
            primary['track'] = 'Site Reliability Engineering (SRE) & Kubernetes Track' if is_senior else 'CI/CD Automation & Cloud Infrastructure Track'
            primary['fit_tier'] = 'Best Fit (Domain Native)'
            primary['why'] = (
                f"Directly accelerates your experience as a {raw_role} into advanced Kubernetes clustering, "
                "Terraform GitOps, multi-region cloud resilience, and AI platform engineering."
            )
            primary['guardrail'] = "Domain native fit."

            fallback['program'] = 'Software & AI Engineering (Scaler Academy)'
            fallback['catalog_code'] = 'Program 1'
            fallback['track'] = 'Advanced Track (High-Level System Design & Scalability)' if is_senior else 'Intermediate Track (Data Structures, Algorithms & LLD)'
            fallback['fit_tier'] = 'Alternative Backend Software Path'
            fallback['why'] = "Alternative path if you want to broaden your profile into core software engineering."

    # =========================================================================
    # SCENARIO 6: SOFTWARE ENGINEERS / DEVELOPERS (SDE / SWE)
    # =========================================================================
    else:
        if inbound_cat == 'P3_FDE':
            if not is_eligible_for_fde:
                primary['program'] = 'Software & AI Engineering (Scaler Academy)'
                primary['catalog_code'] = 'Program 1'
                primary['track'] = 'Beginner Track (Foundations of Programming & Problem Solving)' if is_student else 'Intermediate Track (Data Structures, Algorithms & LLD)'
                primary['fit_tier'] = 'Best Fit (Foundational Prerequisite for FDE)'
                primary['why'] = (
                    f"While you showed high interest in Forward Deployed Engineering, Program 3 requires existing "
                    "software deployment experience (2+ years). Scaler Academy establishes your coding foundation first."
                )
                primary['guardrail'] = "Catalog Gate: FDE requires coding proficiency and 2+ YOE; learner routed to foundational track."

                fallback['program'] = 'AI Forward Deployed Engineer (FDE)'
                fallback['catalog_code'] = 'Program 3'
                fallback['track'] = 'Enterprise AI Integration Track'
                fallback['fit_tier'] = 'Aspirational Goal (Post-Foundations)'
                fallback['why'] = "Target program once foundational data structures and software engineering are mastered."
            else:
                primary['program'] = 'AI Forward Deployed Engineer (FDE)'
                primary['catalog_code'] = 'Program 3'
                primary['track'] = 'Enterprise AI Integration & Production RAG Track'
                primary['fit_tier'] = 'Best Fit (Enterprise AI Deployment)'
                primary['why'] = (
                    f"As a {raw_role} with {raw_exp}, Program 3 trains you to bridge the Enterprise Deployment Gap - "
                    "integrating LLMs, PySpark pipelines, enterprise security, and full-stack client AI solutions."
                )
                primary['guardrail'] = "Catalog Rule 6: Verified coding background matches FDE prerequisite perfectly."

                fallback['program'] = 'AI & Machine Learning with Agentic AI'
                fallback['catalog_code'] = 'Program 4'
                fallback['track'] = 'Advanced Track (Agentic AI & LLMOps)'
                fallback['fit_tier'] = 'Alternative AI Modeling Track'
                fallback['why'] = "Focuses on model fine-tuning and autonomous multi-agent design rather than client consulting."

        elif inbound_cat == 'P4_AIML_AGENTIC':
            if is_student:
                primary['program'] = 'Software & AI Engineering (Scaler Academy)'
                primary['catalog_code'] = 'Program 1'
                primary['track'] = 'Beginner Track (Foundations of Programming & Problem Solving)'
                primary['fit_tier'] = 'Best Fit (Foundational Coding Prerequisite)'
                primary['why'] = (
                    "To build production-grade Agentic AI and fine-tune models, solid programming foundations "
                    "and data structures are required first. Scaler Academy prepares you for advanced AI tracks."
                )
                primary['guardrail'] = "Catalog Rule: Foundation in coding required before autonomous agent design."

                fallback['program'] = 'AI & Machine Learning with Agentic AI'
                fallback['catalog_code'] = 'Program 4'
                fallback['track'] = 'Beginner Track (AI & Machine Learning Foundations)'
                fallback['fit_tier'] = 'Alternative Applied AI Track'
                fallback['why'] = "Direct entry with intensive math and Python machine learning preparation."
            elif exp_bracket in ['EXP_0_1', '0-1 years', 'Fresher / Entry-Level'] or not has_work_experience:
                primary['program'] = 'Software & AI Engineering (Scaler Academy)'
                primary['catalog_code'] = 'Program 1'
                primary['track'] = 'Intermediate Track (Data Structures, Algorithms & LLD)'
                primary['fit_tier'] = 'Best Fit (Core Engineering Foundations for AI)'
                primary['why'] = (
                    f"As an early-career {raw_role}, mastering core algorithmic problem-solving, data structures, "
                    "and low-level system design (LLD) is essential before specializing in autonomous agents and frontier AI."
                )
                primary['guardrail'] = "Catalog Gate: Production Agentic AI engineering requires established DSA and backend coding proficiency."

                fallback['program'] = 'AI & Machine Learning with Agentic AI'
                fallback['catalog_code'] = 'Program 4'
                fallback['track'] = 'Beginner Track (AI & Machine Learning Foundations)'
                fallback['fit_tier'] = 'Alternative Applied AI Track'
                fallback['why'] = "Applied foundational track covering Python, ML mathematics, and prompt-driven agentic workflows."
            else:
                primary['program'] = 'AI & Machine Learning with Agentic AI'
                primary['catalog_code'] = 'Program 4'
                primary['track'] = 'Advanced Track (Agentic AI & LLMOps)'
                primary['fit_tier'] = 'Best Fit (AI / LLM Engineering)'
                primary['why'] = (
                    f"With your software engineering foundation as a {raw_role}, you skip basic programming and dive "
                    "into PyTorch, transformer architectures, vector embeddings, and autonomous multi-agent workflows."
                )
                primary['guardrail'] = "Catalog Tie-Breaker: Software background provides an ideal launchpad for AI Engineering."

                fallback['program'] = 'Software & AI Engineering (Scaler Academy)'
                fallback['catalog_code'] = 'Program 1'
                fallback['track'] = 'Advanced Track (High-Level System Design & Architecture)' if is_senior else 'Intermediate Track (Data Structures, Algorithms & LLD)'
                fallback['fit_tier'] = 'Alternative Product SDE Track'
                fallback['why'] = "Mastering High-Level System Design and concurrency for product company SDE roles."

        elif inbound_cat == 'P5_DEVOPS_CLOUD':
            primary['program'] = 'DevOps, Cloud & AI Platform Engineering'
            primary['catalog_code'] = 'Program 5'
            primary['track'] = 'Site Reliability Engineering (SRE) & Kubernetes Track'
            primary['fit_tier'] = 'Best Fit (Cloud Infrastructure)'
            primary['why'] = (
                f"Complements your development background, qualifying you for hybrid SRE and Platform Engineering roles "
                "managing distributed microservices, CI/CD pipelines, and cloud clusters."
            )
            primary['guardrail'] = "High retention path for developers transitioning to platform engineering."

            fallback['program'] = 'Software & AI Engineering (Scaler Academy)'
            fallback['catalog_code'] = 'Program 1'
            fallback['track'] = 'Backend Architecture & Distributed Systems Track'
            fallback['fit_tier'] = 'Alternative Backend Path'
            fallback['why'] = "Alternative path focusing on microservice architecture and database sharding."

        elif inbound_cat == 'P2_DSML':
            if is_senior:
                primary['program'] = 'Modern Data Science & Machine Learning (DSML)'
                primary['catalog_code'] = 'Program 2'
                primary['track'] = 'Advanced Track (Machine Learning Engineering & Production ML)'
                primary['fit_tier'] = 'Best Fit (Data & ML Engineering Pivot)'
                primary['why'] = (
                    f"With {raw_exp} of engineering experience as a {raw_role}, your coding foundation lets you bypass basic Python "
                    "and advance directly into statistical modeling, feature pipelines, and large-scale enterprise Machine Learning."
                )
                primary['guardrail'] = "Catalog Rule: Experienced engineers transition rapidly into production ML systems."

                fallback['program'] = 'AI & Machine Learning with Agentic AI'
                fallback['catalog_code'] = 'Program 4'
                fallback['track'] = 'Advanced Track (Agentic AI & LLMOps)'
                fallback['fit_tier'] = 'Alternative Frontier AI Track'
                fallback['why'] = "Frontier AI alternative focusing on LLM agents and generative architectures."
            elif is_student:
                primary['program'] = 'Modern Data Science & Machine Learning (DSML)'
                primary['catalog_code'] = 'Program 2'
                primary['track'] = 'Beginner Track (Data Analytics, Python & Business ML)'
                primary['fit_tier'] = 'Best Fit (Foundational Data & ML Track)'
                primary['why'] = (
                    f"As a {raw_role} starting out, Program 2 builds your data querying (SQL), Python programming, "
                    "and business analytics foundations from the ground up for entry-level Data Analyst/Junior Data Scientist roles."
                )
                primary['guardrail'] = "Foundational track calibrated for freshers and early learners."

                fallback['program'] = 'Software & AI Engineering (Scaler Academy)'
                fallback['catalog_code'] = 'Program 1'
                fallback['track'] = 'Beginner Track (Foundations of Programming & Problem Solving)'
                fallback['fit_tier'] = 'Alternative Core Software Track'
                fallback['why'] = "Alternative path building broad software development and problem solving skills."
            else:
                primary['program'] = 'Modern Data Science & Machine Learning (DSML)'
                primary['catalog_code'] = 'Program 2'
                primary['track'] = 'Core Analytics & Machine Learning Track'
                primary['fit_tier'] = 'Best Fit (Data Science & ML Engineering)'
                primary['why'] = (
                    f"With {raw_exp} as a {raw_role}, your programming logic provides an excellent springboard. "
                    "This program equips you with advanced SQL, mathematical modeling, and production ML pipelines."
                )
                primary['guardrail'] = "High retention cohort for developers transitioning to data science."

                fallback['program'] = 'Software & AI Engineering (Scaler Academy)'
                fallback['catalog_code'] = 'Program 1'
                fallback['track'] = 'Intermediate Track (Data Structures, Algorithms & LLD)'
                fallback['fit_tier'] = 'Alternative Core SDE Track'
                fallback['why'] = "If you decide to continue in core software development, Academy prepares you for Tier-1 product roles."

        else:
            if is_senior:
                track_level = 'Advanced Track (High-Level System Design & Scalability)'
                fit_tier = 'Best Fit (Senior Architecture & Scalability)'
                why_text = (
                    f"With {raw_exp} as a {raw_role}, your coding syntax is established. You need architectural depth - "
                    "distributed caching, database sharding, microservices event-driven architectures, and high-level design."
                )
                fallback_prog = 'AI Forward Deployed Engineer (FDE)'
                fallback_code = 'Program 3'
                fallback_track = 'Enterprise AI Integration Track'
                fallback_tier = 'Enterprise AI Leadership Pivot'
                fallback_why = "For senior engineers, FDE offers enterprise client-facing AI consulting with high compensation multiples."
            elif is_student:
                track_level = 'Beginner Track (Foundations of Programming & Problem Solving)'
                fit_tier = 'Best Fit (Foundational Entry & Campus Prep)'
                why_text = (
                    f"As a {raw_role} with {raw_exp}, the Beginner Track builds core programming, "
                    "algorithmic thinking, and foundational Data Structures from scratch to prepare you for Tier-1 product hiring."
                )
                fallback_prog = 'Modern Data Science & Machine Learning (DSML)'
                fallback_code = 'Program 2'
                fallback_track = 'Beginner Track (Data Analytics & Python Foundations)'
                fallback_tier = 'Alternative Analytics Track'
                fallback_why = "A strong entry-level alternative focusing on data analytics and practical problem solving."
            else:
                track_level = 'Intermediate Track (Data Structures, Algorithms & LLD)'
                fit_tier = 'Best Fit (Product SDE Transition)'
                why_text = (
                    f"With {raw_exp} as a {raw_role}, you need algorithmic problem-solving and "
                    "Low-Level Object-Oriented Design (LLD) to crack Tier-1 product company technical bars."
                )
                fallback_prog = 'DevOps, Cloud & AI Platform Engineering'
                fallback_code = 'Program 5'
                fallback_track = 'Cloud Infrastructure Track'
                fallback_tier = 'Alternative Cloud Platform Pivot'
                fallback_why = "A fast-growing alternative if you prefer distributed cloud pipelines over pure algorithmic problem solving."

            primary['program'] = 'Software & AI Engineering (Scaler Academy)'
            primary['catalog_code'] = 'Program 1'
            primary['track'] = track_level
            primary['fit_tier'] = fit_tier
            primary['why'] = why_text
            primary['guardrail'] = "Track level assigned based on YOE maturity and technical foundation."

            fallback['program'] = fallback_prog
            fallback['catalog_code'] = fallback_code
            fallback['track'] = fallback_track
            fallback['fit_tier'] = fallback_tier
            fallback['why'] = fallback_why

    # Assign official program track durations & diagnostic SET scores
    primary['duration'] = get_track_duration(primary.get('program', ''), primary.get('track', ''))
    fallback['duration'] = get_track_duration(fallback.get('program', ''), fallback.get('track', ''))
    primary['sat_score'] = raw_sat_score
    primary['sat_status'] = raw_sat_status
    primary['set_score'] = raw_sat_score
    primary['set_status'] = raw_sat_status
    fallback['sat_score'] = raw_sat_score
    fallback['sat_status'] = raw_sat_status
    fallback['set_score'] = raw_sat_score
    fallback['set_status'] = raw_sat_status

    # -------------------------------------------------------------
    # PULL EMPIRICAL RETENTION & REFUND STATS FROM 13,180 RECORDS
    # -------------------------------------------------------------
    primary_lookup = 'P1_ACADEMY' if 'Academy' in primary['program'] else (
        'P2_DSML' if 'DSML' in primary['program'] else (
            'P3_FDE' if 'FDE' in primary['program'] else (
                'P5_DEVOPS' if 'DevOps' in primary['program'] else 'P4_AIML'
            )
        )
    )
    fallback_lookup = 'P1_ACADEMY' if 'Academy' in fallback['program'] else (
        'P2_DSML' if 'DSML' in fallback['program'] else (
            'P3_FDE' if 'FDE' in fallback['program'] else (
                'P5_DEVOPS' if 'DevOps' in fallback['program'] else 'P4_AIML'
            )
        )
    )

    # When the role is unknown the persona is a guess, so the refund history is matched on experience alone instead of a guessed persona
    _stats_persona = None if (persona_basis == 'unknown' and not is_detected_student) else persona
    primary_stats = _cohort_stats(primary_lookup, _stats_persona, exp_bracket, matrix_data)
    fallback_stats = _cohort_stats(fallback_lookup, _stats_persona, exp_bracket, matrix_data)
    
    primary['retention_rate'] = primary_stats.get('retention_rate', 78.2)
    primary['refund_rate'] = primary_stats.get('refund_rate', 21.8)
    primary['cohort_size'] = primary_stats.get('total', 100)
    primary['refunds_count'] = primary_stats.get('refunds')
    primary['cohort_exact'] = primary_stats.get('exact_available', primary['cohort_size'])
    primary['cohort_detail'] = primary_stats.get('detail')
    primary['risk_tag'] = 'High Retention' if primary['retention_rate'] >= 80 else ('Moderate' if primary['retention_rate'] >= 75 else 'High Risk')

    fallback['retention_rate'] = fallback_stats.get('retention_rate', 75.0)
    fallback['refund_rate'] = fallback_stats.get('refund_rate', 25.0)
    fallback['cohort_size'] = fallback_stats.get('total', 100)
    fallback['refunds_count'] = fallback_stats.get('refunds')
    fallback['cohort_exact'] = fallback_stats.get('exact_available', fallback['cohort_size'])
    fallback['cohort_detail'] = fallback_stats.get('detail')
    fallback['risk_tag'] = 'High Retention' if fallback['retention_rate'] >= 80 else ('Moderate' if fallback['retention_rate'] >= 75 else 'High Risk')

    # Empirical Confidence Calculation (0-100 Score & Tier)
    prim_conf = calculate_confidence(
        primary['program'], conf_inbound_cat, primary['cohort_exact'],
        primary['retention_rate'], raw_sat_status, raw_sat_score, edu_level, inbound_stated, edu_assumed
    )
    fall_conf = calculate_confidence(
        fallback['program'], conf_inbound_cat, fallback['cohort_exact'],
        fallback['retention_rate'], raw_sat_status, raw_sat_score, edu_level, inbound_stated, edu_assumed
    )

    primary['confidence_tier'] = prim_conf['tier']
    primary['confidence_score'] = prim_conf['score']
    primary['confidence_rationale'] = prim_conf['rationale']
    primary['confidence_breakdown'] = prim_conf.get('breakdown', {})

    fallback['confidence_tier'] = fall_conf['tier']
    fallback['confidence_score'] = fall_conf['score']
    fallback['confidence_rationale'] = fall_conf['rationale']
    fallback['confidence_breakdown'] = fall_conf.get('breakdown', {})

    # Clean salutation first name (avoid awkward "Hi Candidate" on phone calls)
    if not name or name in ['Prospective Learner', 'there'] or name.lower().startswith('candidate') or '_' in name or any(c.isdigit() for c in name.split()[0]):
        lead_first_name = 'there'
    else:
        lead_first_name = name.split()[0]
    
    # 1. Opening Dialogue
    org_for_pitch = f"at {prev_org}" if prev_org and prev_org not in ['Current Organization', 'Not Applicable Account', 'Not Applicable', 'NA', 'N/A'] else ""
    exp_phrase = f"with {raw_exp}" if exp_is_explicit else (org_for_pitch if org_for_pitch else "in your current role")
    
    is_data_role = any(k in raw_role.lower() for k in ['data scientist', 'data science', 'machine learning', 'ml engineer', 'ai engineer', 'data analyst', 'bi analyst'])

    if is_student:
        call_opening = (
            f"\"Hi {lead_first_name}, I saw that you're currently {raw_role} ({raw_exp}). "
            "Many candidates at this stage want to build ironclad fundamentals in programming and algorithmic problem solving "
            "so they stand out in product company recruitment. What is the main career milestone you're aiming for?\""
        )
    elif is_data_role:
        call_opening = (
            f"\"Hi {lead_first_name}, I saw you're currently working as a {raw_role} {exp_phrase}. "
            "Many data professionals at this career stage look to move beyond routine reporting and models into building end-to-end "
            "production ML pipelines and deep learning systems. What specific career milestone are you aiming to hit over the next 6 to 12 months?\""
        )
    elif is_non_tech:
        call_opening = (
            f"\"Hi {lead_first_name}, I saw that you're currently working in {raw_role} {exp_phrase}. "
            "A lot of professionals reaching out to us from non-technical backgrounds are looking to make a structured, "
            "long-term transition into tech, but are worried about coding prerequisites. "
            "What has been the main trigger behind your plan to upskill right now?\""
        )
    elif is_senior:
        call_opening = (
            f"\"Hi {lead_first_name}, I noticed you've been working as a {raw_role} {exp_phrase}. "
            "At your seniority, most engineers aren't looking for basic tutorials - they're looking to master large-scale "
            "system architecture, high-level design, and lead engineering teams at top product companies. "
            "Is that the primary transition you're targeting?\""
        )
    else:
        call_opening = (
            f"\"Hi {lead_first_name}, I saw you're currently working as a {raw_role} {exp_phrase}. "
            "Many engineers at this career stage feel ready to move beyond routine project tasks and crack top-tier product SDE roles. "
            "What specific career milestone are you aiming to hit over the next 6 to 12 months?\""
        )

    # 2. Program & Track Value Pitch
    program_pitch = (
        f"\"Based on where your career is right now, the exact program we recommend is {primary['program']}, "
        f"specifically our {primary['track']}. Here is why this matters: we don't put you into a generic one-size-fits-all batch. "
        f"This track is calibrated for your experience level, focusing directly on the core problem-solving, design patterns, and "
        "real-world engineering that top product companies test for in technical rounds.\""
    )

    # 3. Handling Inbound Curiosity / Alternative Course Objection
    inbound_is_same = (
        (inbound_cat == 'P1_ACADEMY' and 'academy' in primary['program'].lower()) or
        (inbound_cat == 'P2_DSML' and 'dsml' in primary['program'].lower()) or
        (inbound_cat == 'P3_FDE' and 'fde' in primary['program'].lower()) or
        (inbound_cat == 'P4_AIML_AGENTIC' and 'agentic' in primary['program'].lower()) or
        (inbound_cat == 'P5_DEVOPS_CLOUD' and 'devops' in primary['program'].lower())
    )
    if inbound_is_same:
        inbound_handling = (
            f"\"Your interest in {primary['program']} is spot on. It directly aligns with your career transition goals, "
            f"and our {primary['track']} gives you a structured, step-by-step foundation without a steep learning cliff.\""
        )
    else:
        if primary.get('retention_rate', 0) >= fallback.get('retention_rate', 0):
            retention_claim = f"gives you a much stronger technical foundation ({primary.get('retention_rate')}% completion rate)"
        else:
            retention_claim = f"provides the most direct alignment with your current background"
            
        inbound_handling = (
            f"\"I also noted your interest in {inbound_prog_raw}. That's an incredible domain, but to be completely honest with you, "
            f"our historical graduation data shows that starting with {primary['program']} {retention_claim}. Once you lock down these engineering fundamentals, transitioning into "
            f"{fallback['program']} becomes vastly easier and faster.\""
        )

    sales_script = {
        'call_opening': call_opening,
        'program_pitch': program_pitch,
        'inbound_handling': inbound_handling
    }

    # 5. Market Intelligence, Audited Placement Metrics & Curriculum Attachment
    prim_market = get_market_intelligence(primary.get('program', ''), raw_role, raw_exp, company_type, primary.get('track', ''))
    fall_market = get_market_intelligence(fallback.get('program', ''), raw_role, raw_exp, company_type, fallback.get('track', ''))

    primary['market_intelligence'] = prim_market
    primary['catalogue_url'] = prim_market.get('catalogue_url', 'https://www.scaler.com/')
    primary['curriculum_modules'] = prim_market.get('curriculum_modules', [])
    primary['career_options'] = {}

    fallback['market_intelligence'] = fall_market
    fallback['catalogue_url'] = fall_market.get('catalogue_url', 'https://www.scaler.com/')
    fallback['curriculum_modules'] = fall_market.get('curriculum_modules', [])
    fallback['career_options'] = {}

    # Synthesize comprehensive, curriculum-grounded reasons for Primary and Fallback
    primary['cohort_evidence'] = cohort_evidence_text(primary.get('cohort_detail'), primary.get('retention_rate'), primary.get('cohort_size'))
    fallback['cohort_evidence'] = cohort_evidence_text(fallback.get('cohort_detail'), fallback.get('retention_rate'), fallback.get('cohort_size'))
    primary['why'] = generate_curriculum_grounded_why(
        primary.get('program', ''), primary.get('track', ''), raw_role, raw_exp,
        primary.get('curriculum_modules', []), primary.get('retention_rate', 78.0),
        primary.get('cohort_size', 100), primary.get('fit_tier', ''), inbound_cat,
        is_primary=True, base_rationale=primary.get('why', ''), persona=persona,
        cohort_detail=primary.get('cohort_detail')
    )

    fallback['why'] = generate_curriculum_grounded_why(
        fallback.get('program', ''), fallback.get('track', ''), raw_role, raw_exp,
        fallback.get('curriculum_modules', []), fallback.get('retention_rate', 75.0),
        fallback.get('cohort_size', 100), fallback.get('fit_tier', ''), inbound_cat,
        is_primary=False, base_rationale=fallback.get('why', ''), persona=persona,
        primary_prog_name=primary.get('program', ''), cohort_detail=fallback.get('cohort_detail')
    )

    return {
        'person': {
            'name': name,
            'email': email,
            'phone': phone,
            'role': raw_role,
            'role_domain': role_domain,
            'company_type': company_type,
            'previous_org': prev_org,
            'previous_org_year': prev_year,
            'experience': raw_exp,
            'enquired_program': inbound_prog_raw,
            'education': raw_edu,
            'education_level': edu_level,
            'sat_score': raw_sat_score,
            'sat_status': raw_sat_status,
            'set_score': raw_sat_score,
            'set_status': raw_sat_status,
            'normalized_persona': persona_name,
            'persona_key': persona,
            'normalized_experience': exp_bracket,
            'inbound_cat': conf_inbound_cat,
            'inbound_stated': inbound_stated,
            'role_provided': role_text_present,
            'role_recognized': role_provided,
            'company_type_provided': str(raw_comp_explicit or '').strip().lower() not in ('', 'nan', 'none', 'null'),
            'persona_inferred_from': persona_inferred_from,
            'persona_basis': persona_basis,
            'experience_basis': ('graduation year' if re.search(r'\(Batch\s*\d{4}\)', str(raw_exp)) else ('organisation start year' if re.search(r'since\s*\d{4}', str(raw_exp)) else ('not provided' if re.search(r'Not Specified|Inferred|Unspecified', str(raw_exp)) else 'stated'))),
            'education_basis': education_basis,
            'education_inferred_from': edu_inferred_from
        },

        'primary': primary,
        'fallback': fallback,
        'sales_script': sales_script,
        'market_intelligence': prim_market,
        'academic_eligibility': {
            'status': acad_status_text if is_detected_student else 'Degree Verified',
            'is_eligible': False if (is_undergrad_incomplete or edu_level == 'BELOW_GRAD') else True,
            'degree_tier': acad_info['degree_tier'],
            'is_pg': is_pg_student,
            'expected_grad_year': expected_grad_year,
            'batch_label': acad_info['batch_label'] if is_detected_student else 'Graduated / Degree Verified',
            'rationale': f"Academic Profile: {acad_info['degree_tier']}. Status: {'Degree Verified' if not is_detected_student else acad_status_text}. Education background satisfies Scaler degree prerequisites."
        }
    }



# ==============================================================================
# DATA-DRIVEN PROGRAM RANKING
# The rule tree above builds the cards. This layer decides WHICH two programs are shown: among the programs a persona is
# eligible for, rank by the refund-funnel retention for that (program, persona, experience) group.
# ==============================================================================
import math

_PROGRAM_NAMES = {
    'P1_ACADEMY': 'Program 1: Software & AI Engineering (Scaler Academy)',
    'P2_DSML': 'Program 2: Modern Data Science & Machine Learning (DSML)',
    'P3_FDE': 'Program 3: AI Forward Deployed Engineer (FDE)',
    'P4_AIML_AGENTIC': 'Program 4: AI & Machine Learning with Agentic AI',
    'P5_DEVOPS_CLOUD': 'Program 5: DevOps, Cloud & AI Platform Engineering',
}
_CODE_OF = {'Program 1': 'P1_ACADEMY', 'Program 2': 'P2_DSML', 'Program 3': 'P3_FDE', 'Program 4': 'P4_AIML_AGENTIC', 'Program 5': 'P5_DEVOPS_CLOUD'}
# Programs each persona can be offered (brochure eligibility: Programs 3 and 4 are for technical learners)
_ELIGIBLE = {
    'NON_TECH': ['P1_ACADEMY', 'P2_DSML'],
    'DATA_ANALYST': ['P2_DSML', 'P4_AIML_AGENTIC', 'P1_ACADEMY', 'P3_FDE'],
    'SWE_BACKEND': ['P1_ACADEMY', 'P4_AIML_AGENTIC', 'P3_FDE', 'P5_DEVOPS_CLOUD', 'P2_DSML'],
    'FRONTEND': ['P1_ACADEMY', 'P4_AIML_AGENTIC', 'P3_FDE', 'P5_DEVOPS_CLOUD', 'P2_DSML'],
    'QA_SDET': ['P1_ACADEMY', 'P5_DEVOPS_CLOUD', 'P4_AIML_AGENTIC', 'P3_FDE', 'P2_DSML'],       # FDE brochure lists SDETs
    'IT_SERVICES': ['P1_ACADEMY', 'P5_DEVOPS_CLOUD', 'P2_DSML', 'P4_AIML_AGENTIC', 'P3_FDE'],  # FDE brochure lists implementation engineers and technical consultants
    'DEVOPS_CLOUD': ['P5_DEVOPS_CLOUD', 'P1_ACADEMY', 'P4_AIML_AGENTIC', 'P3_FDE', 'P2_DSML'],
    'SYSTEMS_ENG': ['P5_DEVOPS_CLOUD', 'P1_ACADEMY', 'P4_AIML_AGENTIC', 'P3_FDE', 'P2_DSML'],
    'LEADERSHIP': ['P1_ACADEMY', 'P3_FDE', 'P4_AIML_AGENTIC', 'P2_DSML'],
    None: ['P1_ACADEMY', 'P2_DSML', 'P4_AIML_AGENTIC', 'P5_DEVOPS_CLOUD', 'P3_FDE'],   # role unknown: not the same as non-tech. About 30% of these leads bought Program 3, 4 or 5, so the model ranks every program
}
STATED_PRIMARY_MARGIN = 10.0    # a stated interest stays the primary unless another program beats it by more than this many points
P3_PENALTY = 0.0               # Program 3 refunded about the same as the other programs once it had a full cohort history (21.7% against 21.9% for Program 1), so it gets no extra penalty. Only used by the rule-based ranking.
STATED_INTEREST_MARGIN = 8.0   # a stated interest within this many points of the second-ranked program is shown as the fallback
_NATIVE = {'DATA_ANALYST': 'P2_DSML', 'DEVOPS_CLOUD': 'P5_DEVOPS_CLOUD', 'SYSTEMS_ENG': 'P5_DEVOPS_CLOUD'}


def _retention_score(retention, n):
    """Conservative retention: the lower bound of an approximate 80% interval, so a small group cannot top the ranking."""
    p = max(0.0, min(1.0, float(retention) / 100.0))
    n = max(1.0, float(n))
    z = 1.28
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return 100.0 * (centre - margin) / (1 + z * z / n)


def _gap_is_clear(ranking, top_code, stated_code, alpha=0.05):
    """True when the refund difference between two programs is statistically clear (two-proportion z test on the matched learners)."""
    try:
        st = {c: s for c, _sc, s in ranking}
        a, b = st[top_code], st[stated_code]
        n1, n2, r1, r2 = a['cohort_size'], b['cohort_size'], a.get('refunds'), b.get('refunds')
        if None in (r1, r2) or not n1 or not n2:
            return True                      # no raw counts (matrix fallback): rely on the score margin alone
        p1, p2 = r1 / n1, r2 / n2
        p = (r1 + r2) / (n1 + n2)
        se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
        if se == 0:
            return False
        z = abs(p1 - p2) / se
        return 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2)))) < alpha
    except Exception:
        return True


def rank_programs(persona_key, exp_key, inbound_cat, inbound_stated, matrix_data=None, set_passed=False, devops_signal=False):
    """Returns [(program_code, score, stats)] best first, for the programs this persona is eligible for."""
    out = []
    codes = list(_ELIGIBLE.get(persona_key, []))
    if persona_key == 'NON_TECH' and set_passed and 'P4_AIML_AGENTIC' not in codes:
        codes.append('P4_AIML_AGENTIC')     # a non-tech lead who passed the diagnostic SET can be shown Program 4 (Beginner Track) as a fallback
    if persona_key == 'NON_TECH' and devops_signal and 'P5_DEVOPS_CLOUD' not in codes:
        codes.append('P5_DEVOPS_CLOUD')     # a non-tech lead who enquired about DevOps, or whose lead sits with the DevOps team, can be shown Program 5 as a fallback
    # a technical lead's stated interest is always a candidate, even if it is not in the persona's usual list
    if inbound_stated and inbound_cat in _PROGRAM_NAMES and inbound_cat not in codes and persona_key != 'NON_TECH':
        codes.append(inbound_cat)
    for code in codes:
        if code == 'P3_FDE' and exp_key not in ('EXP_1_3', 'EXP_3_5', 'EXP_5_PLUS'):
            continue            # FDE needs at least 1 year of coding experience (FDE brochure)
        # the same K nearest past learners the card will show, so the ranking and the card use one set of numbers
        st = _cohort_stats(code, persona_key, exp_key, matrix_data)
        st = dict(st, cohort_size=st.get('total', 0), basis=(st.get('detail') or {}).get('basis', 'matrix estimate'))
        score = _retention_score(st['retention_rate'], st['cohort_size'])
        if inbound_stated and code == inbound_cat:
            score += 3.0        # the lead's stated interest counts, but cannot beat clearly better retention
        if code == 'P3_FDE' and not (inbound_stated and inbound_cat == 'P3_FDE'):
            score -= P3_PENALTY
        if _NATIVE.get(persona_key) == code:
            score += 2.0        # the program built for this persona
        out.append((code, round(score, 2), st))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


_ADV = 'Advanced Track (High-Level System Design & Scalability)'
_INT = 'Intermediate Track (Data Structures, Algorithms & LLD)'


def _apply_batch_by_set(res):
    """Academy batches are allocated by test result. A passed SET moves an experienced lead up one batch."""
    try:
        person = res['person']
        if 'passed' not in str(person.get('set_status', '')).lower():
            return res
        if str(person.get('normalized_persona', '')).startswith(('Student', 'Postgraduate')):
            return res
        exp = person.get('normalized_experience')
        for card, is_primary in ((res['primary'], True), (res['fallback'], False)):
            code = card.get('catalog_code')
            t = str(card.get('track', '')).lower()
            new = None
            if code == 'Program 1':
                if 'intermediate' in t and exp in ('EXP_3_5', 'EXP_5_PLUS'):
                    new = _ADV
                elif 'beginner' in t and exp in ('EXP_1_3', 'EXP_3_5', 'EXP_5_PLUS'):
                    new = _INT
            elif code == 'Program 2' and 'beginner' in t and exp in ('EXP_1_3', 'EXP_3_5', 'EXP_5_PLUS'):
                new = 'Core Analytics & Machine Learning Track'
            elif code == 'Program 4' and 'beginner' in t and exp in ('EXP_1_3', 'EXP_3_5', 'EXP_5_PLUS') and person.get('persona_key') != 'NON_TECH':
                new = 'Advanced Track (Agentic AI & LLMOps)'
            if not new:
                continue
            card['track'] = new
            card['duration'] = get_track_duration(card.get('program', ''), new)
            mi = get_market_intelligence(card.get('program', ''), person.get('role', ''), person.get('experience', ''), person.get('company_type', ''), new)
            card['market_intelligence'] = mi
            card['catalogue_url'] = mi.get('catalogue_url', card.get('catalogue_url'))
            card['curriculum_modules'] = mi.get('curriculum_modules', [])
            card['fit_tier'] = str(card.get('fit_tier', '')) + ' (batch set by the passed SET)'
            card['why'] = generate_curriculum_grounded_why(
                card.get('program', ''), new, person.get('role', ''), person.get('experience', ''), card['curriculum_modules'],
                card.get('retention_rate', 78.0), card.get('cohort_size', 100), card.get('fit_tier', ''), person.get('inbound_cat'),
                is_primary=is_primary, base_rationale='', persona=person.get('persona_key', ''),
                primary_prog_name='' if is_primary else res['primary'].get('program', ''), cohort_detail=card.get('cohort_detail'))
    except Exception:
        pass
    return res


def _set_track(res, card, is_primary, new_track):
    """Change a card's batch and rebuild everything that depends on it (duration, modules, text)."""
    person = res['person']
    card['track'] = new_track
    card['duration'] = get_track_duration(card.get('program', ''), new_track)
    mi = get_market_intelligence(card.get('program', ''), person.get('role', ''), person.get('experience', ''), person.get('company_type', ''), new_track)
    card['market_intelligence'] = mi
    card['catalogue_url'] = mi.get('catalogue_url', card.get('catalogue_url'))
    card['curriculum_modules'] = mi.get('curriculum_modules', [])
    card['why'] = generate_curriculum_grounded_why(
        card.get('program', ''), new_track, person.get('role', ''), person.get('experience', ''), card['curriculum_modules'],
        card.get('retention_rate', 78.0), card.get('cohort_size', 100), card.get('fit_tier', ''), person.get('inbound_cat'),
        is_primary=is_primary, base_rationale='', persona=person.get('persona_key', ''),
        primary_prog_name='' if is_primary else res['primary'].get('program', ''), cohort_detail=card.get('cohort_detail'))


def _fix_unsupported_tracks(res):
    """The DSML brochure defines only a Beginner and an Intermediate batch. Show an experienced learner the Intermediate one."""
    try:
        for card, is_primary in ((res['primary'], True), (res['fallback'], False)):
            if card.get('catalog_code') == 'Program 2' and 'advanced' in str(card.get('track', '')).lower():
                _set_track(res, card, is_primary, 'Intermediate Track (Machine Learning Engineering & Production ML)')
    except Exception:
        pass
    return res


_INTERN_RE = re.compile(r"\b(intern|interns|internship|trainee)\b", re.I)


def _cap_for_input_quality(res):
    """No score reaches 100, and thin inputs lower the ceiling: an internship role, or experience that is only years since graduation."""
    try:
        person = res['person']
        caps = [(95, "No recommendation is scored above 95.")]
        if _INTERN_RE.search(str(person.get('role', ''))):
            caps.append((75, "Capped because the role is an internship."))
        if person.get('experience_basis') == 'graduation year':
            caps.append((85, "Capped because experience is estimated from the graduation year."))
        if person.get('experience_basis') == 'organisation start year':
            caps.append((85, "Capped because experience is estimated from the year the lead joined their organisation."))
        cap, why = min(caps, key=lambda c: c[0])
        for card in (res['primary'], res['fallback']):
            if str(card.get('catalog_code', '')).startswith('Program') and card.get('confidence_score', 0) > cap:
                card['confidence_score'] = cap
                card['confidence_tier'] = 'High' if cap >= 75 else ('Mid' if cap >= 55 else 'Low')
                card['confidence_rationale'] = str(card.get('confidence_rationale', '')) + " " + why
    except Exception:
        pass
    return res


def _cap_for_persona_certainty(res):
    """When the persona was inferred (or unknown) rather than read from the role, confidence cannot be high."""
    try:
        basis = res['person'].get('persona_basis')
        cap = {'inferred': 70, 'unknown': 60}.get(basis)
        if cap is None or str(res['person'].get('normalized_persona', '')).startswith(('Student', 'Postgraduate')):
            return res
        for card in (res['primary'], res['fallback']):
            if card.get('confidence_score', 0) > cap and str(card.get('catalog_code', '')).startswith('Program'):
                card['confidence_score'] = cap
                card['confidence_tier'] = 'High' if cap >= 75 else ('Mid' if cap >= 55 else 'Low')
                card['confidence_rationale'] = str(card.get('confidence_rationale', '')) + (
                    " Capped because the persona was inferred from other fields." if basis == 'inferred' else " Capped because the role was not provided.")
    except Exception:
        pass
    return res


_LEVEL = (('beginner', 'Beg', 'Beginner'), ('intermediate', 'Int', 'Intermediate'), ('advanced', 'Adv', 'Advanced'))


def _pct(v, nd=1):
    return f"{round(100 * float(v), nd):g}%"


def _in10(rate):
    """A refund rate in plain words: 0.212 -> 'about 21 in every 100 learners'."""
    k = int(round(float(rate) * 100))
    return "fewer than 1 in every 100 learners" if k <= 0 else f"about {k} in every 100 learners"


def _plain(k, n):
    """k refunded of n learners, in plain words with the real numbers: '444 of 2,099 learners refunded (21.2%), about 21 in every 100 learners'."""
    return f"{k:,} of {n:,} learners refunded ({_pct(k / n)}), {_in10(k / n)}"


def _refund_card_parts(card, is_primary_card=True):
    """Refund facts for one card. Every part is built on its own: if one is missing or odd, the others still appear."""
    code = _CODE_OF.get(str(card.get('catalog_code', '')))
    if not code:
        return
    ph = d = None
    bh = {}
    try:
        ph = learned.program_history(code)
    except Exception:
        pass
    try:
        d = card.get('cohort_detail')
        if d and not (d.get('n') or 0) > 0:
            d = None
    except Exception:
        d = None
    try:
        bh = learned.batch_history(code) or {}
    except Exception:
        bh = {}
    t = str(card.get('track', '')).lower()
    mine = next(((k, name) for key, k, name in _LEVEL if key in t), None)
    ov = None
    try:
        ov = learned.overall_refund()
    except Exception:
        pass

    items, lines = [], []
    try:
        if ph and ph.get('n'):
            kk = int(round(ph['refund_rate'] * ph['n']))
            items.append(f"<b>This program:</b> {_plain(kk, ph['n'])}" + (f". All five programs together: {_pct(ov)} refunded, {_in10(ov)}." if ov else "."))
            lines.append(f"This program: {_plain(kk, ph['n'])}.")
    except Exception:
        pass
    try:
        if d:
            ea = d.get('exact_available') or 0
            if d.get('exact_used') == d['n'] and ea > d['n'] and d.get('exact_refunds') is not None:
                gk, gn = d['exact_refunds'], ea      # whole exact group, not only its newest 40
                txt = f"{_plain(gk, gn)}. These are all past learners of this program with the same persona and experience band."
            elif d.get('exact_used') == d['n']:
                txt = f"{_plain(d['refunds'], d['n'])}. These are past learners of this program with the same persona and experience band."
            else:
                txt = (f"{_plain(d['refunds'], d['n'])}. Only {ea} past learners of this program match this persona and experience band exactly"
                       + (f" ({d.get('exact_refunds', 0)} of them refunded)" if ea else "") + f", so the {d['n']} closest are used: {d.get('basis', 'nearest profiles')}.")
            items.append(f"<b>Learners like this lead:</b> {txt} Only learners who filled the onboarding form are included; those who skip it refund more.")
            lines.append(f"Learners like this lead: {_plain(d['refunds'], d['n'])}.")
    except Exception:
        pass
    try:
        if mine and bh.get(mine[0], {}).get('n', 0) >= 100:
            x = bh[mine[0]]
            kb = int(round(x['refund_rate'] * x['n']))
            items.append(f"<b>{mine[1]} batch of this program:</b> {_plain(kb, x['n'])}.")
            lines.append(f"Its {mine[1]} batch: {_plain(kb, x['n'])}.")
    except Exception:
        pass
    card['refund_history'] = lines
    try:
        levels = [{'key': k, 'label': name, 'rate': bh[k]['refund_rate'], 'n': bh[k]['n'], 'current': bool(mine and mine[0] == k)}
                  for _key, k, name in _LEVEL if k in bh and bh[k]['n'] >= 100]
        card['refund_analytics'] = {
            'overall': ov,
            'programs': [dict(p, current=(p['code'] == code)) for p in learned.all_programs_history()],
            'similar': ({'refunds': d['refunds'], 'n': d['n'], 'rate': round(d['refunds'] / d['n'], 4), 'basis': d.get('basis'), 'exact': d.get('exact_available'), 'exact_refunds': d.get('exact_refunds')} if d else None),
            'batches': levels if len(levels) >= 2 else [],
        }
    except Exception:
        pass
    # The reasoning text. Only ever appended to, and only when there is something real to add.
    try:
        if items and 'Refund record' not in str(card.get('why', '')):
            card['why'] = str(card.get('why', '')).rstrip() + '<br><br><b>Refund record</b><br>' + '<br>'.join(items)
    except Exception:
        pass


def _attach_history(res):
    """Refund facts from the refund funnel on each card. A problem with one card or one fact never affects the rest of the result."""
    for key in ('primary', 'fallback'):
        try:
            _refund_card_parts(res[key])
        except Exception:
            pass
    return res


FDE_TRACK = 'AI Forward Deployed Engineer Track'
_OLD_FDE_TRACKS = ('Enterprise AI Integration & Production RAG Track', 'Enterprise AI Integration & Client Systems Track', 'Enterprise AI Integration Track')


def _single_fde_track(res):
    """Program 3 has one track, so every card shows the same name wherever the older rules had set a variant."""
    def fix(x):
        if isinstance(x, str):
            for old in _OLD_FDE_TRACKS:
                if old in x:
                    x = x.replace(old, FDE_TRACK)
            return x
        if isinstance(x, dict):
            return {k: fix(v) for k, v in x.items()}
        if isinstance(x, list):
            return [fix(v) for v in x]
        return x
    try:
        return fix(res)
    except Exception:
        return res


NON_TECH_ADVANCED_ROW = True        # third row of a non-tech lead may show FDE / AI-ML / DevOps (switch off to compare)
ALSO_CONSIDER_MIN = 0.15      # a third program is shown only when it is really bought at least 15% of the time for leads like this (measured chance)
HIGH_RIGHT, MID_RIGHT = 65, 50   # measured confidence: the first program was right 65%+ of the time = High, 50 to 64% = Mid, below = Low


def _measured_confidence(res):
    """Replace the rule-based confidence with a measured one: how often a program the model scored like this was really bought, on months
    the model had not seen. Leads with no model ranking (students, gates) keep the rule-based score and say so."""
    try:
        person = res.get('person') or {}
        lr = person.get('learned_ranking') or []
        if not lr or not learned.calibration_available():
            for k in ('primary', 'fallback'):
                res[k]['confidence_basis'] = 'rules'
            return res
        chance = {c['code']: float(c['enrol']) for c in lr}
        n_learners = int((((_load_cal() or {}).get('pairs') or 0)) / 5)
        for key in ('primary', 'fallback'):
            card = res[key]
            code = _CODE_OF.get(str(card.get('catalog_code', '')))
            if code not in chance:
                card['confidence_basis'] = 'rules'
                continue
            rate = learned.calibrated(chance[code])
            pct = int(round(100 * rate))
            card['confidence_rules'] = card.get('confidence_score')
            card['confidence_score'] = pct
            card['confidence_basis'] = 'measured'
            if key == 'primary':
                card['confidence_tier'] = 'High' if pct >= HIGH_RIGHT else ('Mid' if pct >= MID_RIGHT else 'Low')
                card['confidence_label'] = f"Right about {pct}% of the time for leads like this"
            else:
                card['confidence_tier'] = 'Mid' if pct >= 20 else 'Low'
                card['confidence_label'] = f"Bought by about {pct}% of leads like this"
            card['confidence_rationale'] = (f"Measured, not estimated: on months the model had not seen, programs it scored like this one were bought {pct}% of the time"
                                            f" (from forecasts of about {n_learners:,} past learners).")
    except Exception:
        pass
    return res


def _load_cal():
    try:
        return learned._load().get('calibration')
    except Exception:
        return None


def _add_also_consider(res):
    """The third, lighter row: the lead's own enquiry when it is not already shown (so what the lead asked about is always visible), else the next
    program the model ranks if it has a real measured chance. Not a full card."""
    try:
        res['also_consider'] = None
        person = res.get('person') or {}
        lr = person.get('learned_ranking') or []
        if not lr or str(person.get('normalized_persona', '')).startswith(('Student', 'Postgraduate')):
            return res
        shown = {_CODE_OF.get(str(res['primary'].get('catalog_code', ''))), _CODE_OF.get(str(res['fallback'].get('catalog_code', '')))}
        asked = person.get('inbound_cat') if person.get('inbound_stated') else None
        nxt = next((c for c in lr if c.get('code') == asked and asked not in shown), None) if asked else None      # the lead's own enquiry
        is_enquiry = nxt is not None
        if nxt is None:
            nxt = next((c for c in lr if c.get('code') in _CODE_OF.values() and c.get('code') not in shown), None)
        advanced = False
        if NON_TECH_ADVANCED_ROW and not is_enquiry and person.get('persona_key') == 'NON_TECH' and person.get('persona_basis') != 'unknown':
            # A non-tech lead is never shown FDE, AI/ML or DevOps as the Recommended or Fallback, but 39% of them buy one of these.
            # So the third row may show the one the model rates highest, when it has a real measured chance. The lead's own enquiry is never replaced.
            allp = person.get('learned_enrol_all') or {}
            cal = (lambda v: learned.calibrated(float(v))) if learned.calibration_available() else (lambda v: float(v))
            cand = [(cal(allp[c]), c) for c in ('P3_FDE', 'P4_AIML_AGENTIC', 'P5_DEVOPS_CLOUD') if c in allp and c not in shown]
            if cand:
                top = max(cand)
                if top[0] >= ALSO_CONSIDER_MIN:
                    nxt = {'code': top[1], 'enrol': allp[top[1]]}
                    advanced = True
        if not nxt:
            return res
        chance = learned.calibrated(float(nxt.get('enrol', 0))) if learned.calibration_available() else float(nxt.get('enrol', 0))
        if chance < ALSO_CONSIDER_MIN and not is_enquiry:
            return res
        code = nxt['code']
        ph = learned.program_history(code) or {}
        name = _PROGRAM_NAMES.get(code, code)
        low = chance < ALSO_CONSIDER_MIN                    # only the lead's own enquiry can get here with a low chance
        res['also_consider'] = {
            'label': 'Lead asked about' if low else 'Also consider', 'low_chance': low,
            'catalog_code': next((k for k, v in _CODE_OF.items() if v == code), code), 'program': name, 'chance_pct': round(100 * chance),
            'program_refund_rate': round(100 * float(ph['refund_rate']), 1) if ph.get('refund_rate') is not None else None,
            'reason': (f"What the lead asked about. Few leads like this one bought it (about {round(100 * chance)}%), so it is shown for information, not as a suggestion." if low
                       else ("What the lead asked about. " if is_enquiry else "") + f"Bought by about {round(100 * chance)}% of leads like this one."),
            'is_enquiry': is_enquiry, 'advanced_for_non_tech': advanced,
        }
    except Exception:
        res['also_consider'] = None
    return res


def _cap_nontech_p4(res):
    """Program 4 for a non-tech lead is a conditional suggestion (Beginner Track), so its confidence never reads 'High'."""
    try:
        if res['person'].get('persona_key') == 'NON_TECH' and res['fallback'].get('catalog_code') in ('Program 4', 'Program 5'):
            f = res['fallback']
            if (f.get('confidence_score') or 0) > 65:
                f['confidence_score'] = 65
                f['confidence_tier'] = 'Mid'
                f['confidence_rationale'] = 'Conditional fallback for a non-tech lead.'
    except Exception:
        pass
    return res


def _cap_fallback_confidence(res):
    """The fallback is the second choice, so its confidence cannot be higher than the primary's."""
    try:
        p, f = res['primary'], res['fallback']
        if f.get('confidence_score', 0) > p.get('confidence_score', 0) and p.get('confidence_score') is not None:
            f['confidence_score'] = p['confidence_score']
            f['confidence_tier'] = p.get('confidence_tier', f.get('confidence_tier'))
            f['confidence_rationale'] = str(f.get('confidence_rationale', '')) + " Capped at the primary program's confidence."
    except Exception:
        pass
    return res


def evaluate_lead_profile(lead_dict, matrix_data=None):
    base = _evaluate_core(lead_dict, matrix_data)
    try:
        return _single_fde_track(_attach_history(_add_also_consider(_measured_confidence(_cap_fallback_confidence(_cap_nontech_p4(_cap_for_input_quality(_cap_for_persona_certainty(_apply_batch_by_set(_fix_unsupported_tracks(_rerank_programs(base, lead_dict, matrix_data)))))))))))
    except Exception:
        return _single_fde_track(_attach_history(_add_also_consider(_measured_confidence(_cap_fallback_confidence(_cap_nontech_p4(_cap_for_input_quality(_cap_for_persona_certainty(_apply_batch_by_set(_fix_unsupported_tracks(base))))))))))


def _rerank_programs(base, lead_dict, matrix_data):
    person = base.get('person', {})
    pk = person.get('persona_key')
    if person.get('persona_basis') == 'unknown':
        pk = None                                   # persona unknown: rank on experience-only refund history
    elif pk not in _ELIGIBLE:
        return base
    if str(person.get('normalized_persona', '')).startswith(('Student', 'Postgraduate')):
        return base
    prim, fall = base['primary'], base['fallback']
    code_p = _CODE_OF.get(str(prim.get('catalog_code', '')))
    code_f = _CODE_OF.get(str(fall.get('catalog_code', '')))
    if not code_p or not code_f:
        return base                                   # eligibility gates (below graduation etc.) are not re-ranked
    set_passed = 'passed' in str(person.get('set_status', '')).lower()
    set_p4 = (pk == 'NON_TECH' and set_passed)         # Program 4 is offered to this lead only as the fallback
    _team1 = str((lead_dict.get('crm') or {}).get('which_bda_team') or '').split('/')[0].strip().lower()
    devops_nt = (pk == 'NON_TECH' and ((person.get('inbound_cat') == 'P5_DEVOPS_CLOUD' and bool(person.get('inbound_stated'))) or _team1 == 'devops'))
    ranking = rank_programs(pk, person.get('normalized_experience'), person.get('inbound_cat'), person.get('inbound_stated'), matrix_data, set_passed=set_passed, devops_signal=devops_nt)
    if _INTERN_RE.search(str(person.get('role', ''))):
        ranking = [r for r in ranking if r[0] in ('P1_ACADEMY', 'P2_DSML')]     # an intern is early-career: Academy or DSML only
        if len(ranking) < 2:
            return base
    cards = {code_p: prim, code_f: fall}
    results = {code_p: base}
    chosen = []
    from_fb = set()                                   # programs whose card came from a fallback card of the rule tree
    order = [c for c, _sc, _st in ranking]
    stated = person.get('inbound_cat') if person.get('inbound_stated') else None
    scores = {c: sc for c, sc, _st in ranking}
    learned_order = None
    if learned.available():
        crm = dict(lead_dict.get('crm') or {})
        crm.setdefault('role', lead_dict.get('role'))
        if not crm.get('program_type'):
            _pt = str(lead_dict.get('program') or '').lower()      # the interest, mapped to the CRM's own categories
            crm['program_type'] = ('DevOps' if re.search(r'devops|program 5|cloud', _pt) else 'fde' if re.search(r'fde|forward|program 3', _pt)
                                   else 'ai_ml' if re.search(r'agentic|aiml|ai ?(and|&|/)? ?ml|program 4|ai_ml', _pt)
                                   else 'Data_Science' if re.search(r'data|dsml|program 2', _pt) else 'Academy' if _pt else None)
        crm.setdefault('company_type', lead_dict.get('company type') or lead_dict.get('company_type'))
        crm.setdefault('orgname', lead_dict.get('previous org name'))
        crm.setdefault('orgyear', lead_dict.get('previous org year'))
        crm.setdefault('test_passed_flag', 1 if 'passed' in str(lead_dict.get('set_status', '')).lower() else 0)
        learned_order = learned.rank(crm, list(order), stated=stated)
        try:                                           # the model's chance for all five programs, for the third row of non-tech leads
            _pr = learned.predict(crm) or {}
            base['person']['learned_enrol_all'] = {learned.P_TO_CODE[k]: v['enrol'] for k, v in _pr.items() if k in learned.P_TO_CODE}
        except Exception:
            pass
    if learned_order:
        order = [x['code'] for x in learned_order]
        base['person']['learned_ranking'] = learned_order
        # Non-tech leads switching into tech: Academy is the program built for them, so it goes first when Academy and DSML are the top two,
        # unless the lead enquired about DSML (then the enquiry stays first). Evidence, Feb-Oct 2026 cohorts, non-tech roles:
        #  - enquired Academy: Academy buyers refunded 12.0% (108 learners), DSML buyers 28.0% (150); on the held-out Aug-Oct months 13.2% vs 22.9%
        #  - enquired DSML: DSML buyers 27.2% (217), Academy buyers 31.6% (19), so no case for overriding the enquiry
        if pk == 'NON_TECH' and stated != 'P2_DSML' and 'P1_ACADEMY' in order[:2] and 'P2_DSML' in order[:2] and order.index('P2_DSML') < order.index('P1_ACADEMY'):
            order.remove('P1_ACADEMY'); order.insert(0, 'P1_ACADEMY')
        # Non-tech leads with a DevOps enquiry or DevOps team: Program 5 is the fallback (63% of such leads bought it, and they stayed at the same rate as other non-tech learners).
        if devops_nt and 'P5_DEVOPS_CLOUD' in order and len(order) > 1:
            order.remove('P5_DEVOPS_CLOUD'); order.insert(1, 'P5_DEVOPS_CLOUD')
    elif stated in order and order.index(stated) >= 1 and (
            scores[order[0]] - scores[stated] <= STATED_PRIMARY_MARGIN or not _gap_is_clear(ranking, order[0], stated)):
        order.remove(stated); order.insert(0, stated)      # the lead's own interest stays first unless the data clearly favours another program
    if not learned_order and stated in order and order.index(stated) >= 2:
        if scores[stated] >= scores[order[1]] - STATED_INTEREST_MARGIN:
            order.remove(stated); order.insert(1, stated)    # the lead's own interest is shown as the fallback when the data does not clearly rule it out
    if set_p4 and len(order) > 1 and order[0] == 'P4_AIML_AGENTIC':
        order.remove('P4_AIML_AGENTIC'); order.insert(1, 'P4_AIML_AGENTIC')      # Program 4 is only ever the fallback for these leads: second, not skipped
    ranking = [r for c in order for r in ranking if r[0] == c]
    for code, score, _st in ranking:
        if ((set_p4 and code == 'P4_AIML_AGENTIC') or (devops_nt and code == 'P5_DEVOPS_CLOUD')) and not chosen:
            continue                                  # never the primary for these leads
        if code not in cards:
            res = _evaluate_core(lead_dict, matrix_data, force_inbound=code)
            card = res['primary']
            if _CODE_OF.get(str(card.get('catalog_code', ''))) != code:
                fb = res.get('fallback') or {}
                if set_p4 and code == 'P4_AIML_AGENTIC' and _CODE_OF.get(str(fb.get('catalog_code', ''))) == code:
                    card = fb                         # the rule tree's Program 4 Beginner Track card
                    card['fit_tier'] = 'Conditional Fit (passed the diagnostic SET)'
                    card['confidence_score'] = min(card.get('confidence_score', 65) or 65, 65)      # a conditional suggestion, so never a 'High' confidence
                    card['confidence_tier'] = 'Mid'
                    card['confidence_rationale'] = 'Conditional fallback: a non-tech lead who passed the diagnostic SET, shown the Beginner Track of Program 4.'
                elif devops_nt and code == 'P5_DEVOPS_CLOUD':
                    # the rule tree has no Program 5 card for a non-tech role: build it as for a support engineer, then give it THIS lead's own cohort numbers
                    res5 = _evaluate_core(dict(lead_dict, role='Support Engineer'), matrix_data, force_inbound=code)
                    c5 = res5['primary']
                    if _CODE_OF.get(str(c5.get('catalog_code', ''))) != code:
                        continue
                    card = c5
                    card['fit_tier'] = 'Conditional Fit (DevOps enquiry)'
                    card['retention_rate'] = _st.get('retention_rate', card.get('retention_rate'))
                    card['cohort_size'] = _st.get('total', card.get('cohort_size'))
                    card['refunds_count'] = _st.get('refunds')
                    card['cohort_exact'] = _st.get('exact_available', card['cohort_size'])
                    card['cohort_detail'] = _st.get('detail')
                    card['cohort_evidence'] = cohort_evidence_text(card.get('cohort_detail'), card.get('retention_rate'), card.get('cohort_size'))
                    card['confidence_score'] = min(card.get('confidence_score', 65) or 65, 65)
                    card['confidence_tier'] = 'Mid'
                    card['confidence_rationale'] = 'Conditional fallback: a non-tech lead who enquired about DevOps, or whose lead sits with the DevOps team.'
                    res = res5
                elif _CODE_OF.get(str(fb.get('catalog_code', ''))) == code:
                    card = fb                         # the rule tree builds this program as its own fallback card (for example Academy for a data analyst): use it
                    card['fit_tier'] = 'Ranked by the learned model'
                    from_fb.add(code)
                elif pk is None and code in ('P3_FDE', 'P4_AIML_AGENTIC', 'P5_DEVOPS_CLOUD'):
                    # role unknown: the rule tree assumes non-tech and has no card for this program. Build the program's own card (track, modules)
                    # as for a generic technical role, then give it THIS lead's cohort numbers. The call script stays the lead's own.
                    res_u = _evaluate_core(dict(lead_dict, role='Support Engineer' if code == 'P5_DEVOPS_CLOUD' else 'Software Engineer'), matrix_data, force_inbound=code)
                    cu = res_u['primary']
                    if _CODE_OF.get(str(cu.get('catalog_code', ''))) != code:
                        continue
                    card = cu
                    card['fit_tier'] = 'Ranked by the learned model (role not given)'
                    card['retention_rate'] = _st.get('retention_rate', card.get('retention_rate'))
                    card['cohort_size'] = _st.get('total', card.get('cohort_size'))
                    card['refunds_count'] = _st.get('refunds')
                    card['cohort_exact'] = _st.get('exact_available', card['cohort_size'])
                    card['cohort_detail'] = _st.get('detail')
                    card['cohort_evidence'] = cohort_evidence_text(card.get('cohort_detail'), card.get('retention_rate'), card.get('cohort_size'))
                    card['confidence_score'] = min(card.get('confidence_score', 65) or 65, 65)
                    card['confidence_tier'] = 'Mid'
                    card['confidence_rationale'] = 'The lead gave no usable role, so this program is ranked from the enquiry, team and event only.'
                    res = base
                else:
                    continue                          # the rule tree would not offer this program to this lead
            cards[code] = card
            results[code] = res
        chosen.append(code)
        if len(chosen) == 2:
            break
    if len(chosen) < 2 or (chosen[0] == code_p and chosen[1] == code_f):
        return base
    new_p, new_f = cards[chosen[0]], cards[chosen[1]]
    role, exp = person.get('role', ''), person.get('experience', '')
    inbound = person.get('inbound_cat')
    for card, is_primary in ((new_p, True), (new_f, False)):
        card['why'] = generate_curriculum_grounded_why(
            card.get('program', ''), card.get('track', ''), role, exp, card.get('curriculum_modules', []),
            card.get('retention_rate', 78.0), card.get('cohort_size', 100), card.get('fit_tier', ''), inbound,
            is_primary=is_primary, base_rationale='', persona=pk,
            primary_prog_name='' if is_primary else new_p.get('program', ''), cohort_detail=card.get('cohort_detail'))
    out = dict(base)
    out['primary'], out['fallback'] = new_p, new_f
    # The call script comes from a run whose primary is the program now shown first; its fallback names are swapped for ours
    src_res = results.get(chosen[0], base)
    script = dict(src_res.get('sales_script', {}))
    old_p, old_f = src_res['primary'], src_res['fallback']
    # The script was written around the rule tree's own first and second program. Rename both to the programs shown now, all at once
    # (through placeholders) so that a swap of two programs does not undo itself.
    swap_pairs = [(str(old_p.get('program', '')), str(new_p.get('program', ''))), (str(old_p.get('track', '')), str(new_p.get('track', ''))),
                  (str(old_f.get('program', '')), str(new_f.get('program', ''))), (str(old_f.get('track', '')), str(new_f.get('track', '')))]
    swap_pairs = [(o, n) for o, n in swap_pairs if o and o != n]
    for key, text in list(script.items()):
        if isinstance(text, str):
            for i, (old, _new) in enumerate(swap_pairs):
                text = text.replace(old, f'\u0001{i}\u0002')
            for i, (_old, new) in enumerate(swap_pairs):
                text = text.replace(f'\u0001{i}\u0002', new)
            script[key] = text
    out['sales_script'] = script
    out['market_intelligence'] = new_p.get('market_intelligence', base.get('market_intelligence'))
    out['person'] = dict(person, ranked_programs=[{'code': c, 'score': sc} for c, sc, _ in ranking])
    return out

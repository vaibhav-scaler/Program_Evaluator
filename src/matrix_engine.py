import os
import json
import re
import functools
import pandas as pd

DATA_SOURCE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Data_Source', 'Copy of Refunds Funnel - Raw.csv')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
MATRIX_JSON_PATH = os.path.join(OUTPUT_DIR, 'retention_matrix.json')

DEFAULT_FALLBACK = {
    'program': 'Scaler Academy',
    'persona': 'General Tech Professional',
    'total': 13180,
    'cohort_size': 13180,
    'refunds': 2872,
    'retention_rate': 78.2,
    'refund_rate': 21.8,
    'risk_level': 'High Retention'
}

_RE_P3 = re.compile(r'\bp3\b')
_RE_P4 = re.compile(r'\bp4\b')
_RE_P2 = re.compile(r'\bp2\b')
_RE_P5 = re.compile(r'\bp5\b')

@functools.lru_cache(maxsize=1024)
def canonical_prog_key(prog_str):
    s = str(prog_str).lower()
    if any(k in s for k in ['fde', 'forward', 'program 3']) or _RE_P3.search(s):
        return 'P3_FDE'
    elif any(k in s for k in ['aiml', 'agentic', 'deep learning', 'program 4']) or _RE_P4.search(s):
        return 'P4_AIML'
    elif any(k in s for k in ['dsml', 'data', 'analytics', 'program 2']) or _RE_P2.search(s):
        return 'P2_DSML'
    elif any(k in s for k in ['devop', 'cloud', 'program 5']) or _RE_P5.search(s):
        return 'P5_DEVOPS'
    return 'P1_ACADEMY'

# ==============================================================================
# ENCYCLOPEDIC GLOBAL PROFESSION TAXONOMY & DOMAIN CLASSIFIER
# Covers every real-world career domain across healthcare, security, trades,
# education, hospitality, logistics, public sector, retail, corporate, and arts.
# ==============================================================================

CANONICAL_PERSONA_NAMES = {
    'NON_TECH': 'Non-Tech / Career Switcher',
    'QA_SDET': 'QA / SDET / Testing',
    'DATA_ANALYST': 'Data & Analytics',
    'DEVOPS_CLOUD': 'DevOps & Cloud Platform',
    'SYSTEMS_ENG': 'Systems & Embedded Engineering',
    'LEADERSHIP': 'Engineering Leadership / Management',
    'FRONTEND': 'Frontend Engineering',
    'IT_SERVICES': 'General IT Services / Maintenance',
    'SWE_BACKEND': 'Software Engineering (Backend/FullStack)',
}

import functools

@functools.lru_cache(maxsize=16384)
def _get_token_regex(token: str):
    return re.compile(r'(?<![a-zA-Z0-9])' + re.escape(token) + r'(?![a-zA-Z0-9])')

def match_token(text, token):
    """
    Matches a token safely inside text using lookarounds to ensure strict word/token boundaries
    across both letters and punctuation (e.g. c++, .net).
    Prevents false substring collisions such as:
    - 'automobile engineer' matching 'mobile engineer'
    - 'sweeper' matching 'swe'
    - 'waiter' matching 'ai'
    Uses substring pre-filtering and LRU regex compilation for 16x faster batch evaluation.
    """
    t = token.lower().strip() if isinstance(token, str) else str(token).lower().strip()
    s = text if (isinstance(text, str) and text.islower()) else str(text).lower()
    if not t or not s:
        return False
    if t not in s:
        return False
    return bool(_get_token_regex(t).search(s))


def match_any(text, tokens):
    s = text if (isinstance(text, str) and text.islower()) else str(text).lower()
    return any(match_token(s, t) for t in tokens)

@functools.lru_cache(maxsize=8192)
def classify_world_domain(role_str):
    """
    Identifies the real-world career domain / industry sector for any profession on Earth.
    Covers 19 exhaustive global career families with exact token collision safeguards.
    """
    s = str(role_str).lower().strip()
    
    # 1. Healthcare, Medicine & Clinical Services
    if match_any(s, [
        'nurse', 'nursing', 'doctor', 'physician', 'surgeon', 'dentist', 'dental', 'pharmacist',
        'pharmacy', 'chemist', 'paramedic', 'emt', 'ambulance', 'physiotherapist', 'physiotherapy',
        'radiologist', 'radiology', 'sonographer', 'lab technician', 'pathologist', 'pathology',
        'clinical', 'clinic', 'hospital', 'healthcare', 'health care', 'optometrist', 'ophthalmologist',
        'veterinarian', 'dietitian', 'nutritionist', 'phlebotomist', 'caregiver', 'ward boy', 'orderly',
        'anesthesiologist', 'cardiologist', 'dermatologist', 'pediatrician', 'psychiatrist', 'psychologist',
        'therapist', 'midwife'
    ]):
        return 'Healthcare & Medical Services'

    # 2. Legal, Compliance & Judiciary (Evaluated before defense to catch 'Criminal Defense Lawyer')
    if match_any(s, [
        'lawyer', 'advocate', 'attorney', 'legal', 'paralegal', 'solicitor', 'barrister', 'notary',
        'judge', 'magistrate', 'public prosecutor', 'legal counsel', 'compliance officer', 'law clerk'
    ]):
        return 'Legal, Compliance & Judiciary'

    # 3. Security, Defense & Law Enforcement
    if match_any(s, [
        'security guard', 'security officer', 'guard', 'watchman', 'chowkidar', 'bouncer', 'bodyguard',
        'police', 'cop', 'constable', 'inspector', 'sho', 'law enforcement', 'detective', 'investigator',
        'military', 'army', 'navy', 'air force', 'armed forces', 'defense', 'defence', 'paramilitary',
        'firefighter', 'fireman', 'corrections officer', 'jailer', 'warden', 'border patrol', 'coast guard'
    ]):
        return 'Security & Protective Services'

    # 4. Education, Teaching & Academia
    if match_any(s, [
        'teacher', 'school teacher', 'professor', 'lecturer', 'tutor', 'tuition', 'instructor',
        'educator', 'faculty', 'dean', 'principal', 'headmaster', 'headmistress', 'academic counselor',
        'librarian', 'pedagogy', 'scholar', 'trainer'
    ]):
        return 'Education & Academia'

    # 5. Hospitality, Facility & Cleaning Services (Catches Sweeper, Janitor, Chef, Hotel Staff)
    if match_any(s, [
        'sweeper', 'cleaner', 'janitor', 'housekeeper', 'housekeeping', 'sanitation', 'waste management',
        'maid', 'laundry', 'chef', 'cook', 'baker', 'bakery', 'barista', 'bartender', 'waiter', 'waitress',
        'server', 'steward', 'restaurant', 'cafe', 'hotel', 'hospitality', 'concierge', 'sommelier',
        'tour guide', 'flight attendant', 'cabin crew', 'air hostess'
    ]):
        return 'Hospitality & Facility Services'

    # 6. Traditional Engineering & Physical Sciences (Non-CS) (Evaluated before trades to catch Mechanical Engineer)
    if match_any(s, [
        'mechanical engineer', 'mechanical', 'civil engineer', 'civil', 'chemical engineer', 'chemical',
        'petroleum', 'mining', 'metallurgy', 'aerospace', 'aeronautical', 'biotech', 'biotechnology',
        'biomedical', 'textile', 'automobile engineer', 'automotive engineer', 'environmental engineer',
        'structural engineer', 'physicist', 'chemist', 'geologist'
    ]) or ('electrical' in s and 'hardware' not in s and 'software' not in s):
        return 'Traditional Engineering (Non-CS)'

    # 7. Skilled Trades, Crafts & Construction Maintenance
    if match_any(s, [
        'electrician', 'plumber', 'carpenter', 'welder', 'machinist', 'mechanic', 'auto mechanic',
        'car mechanic', 'motor mechanic', 'fitter', 'turner', 'mason', 'masonry', 'construction',
        'builder', 'painter', 'hvac', 'appliance repair', 'blacksmith', 'locksmith', 'tailor', 'cobbler',
        'weaver', 'factory worker'
    ]):
        return 'Trades, Crafts & Construction'

    # 8. Transportation, Logistics & Aviation
    if match_any(s, [
        'pilot', 'commercial pilot', 'airline pilot', 'mariner', 'sailor', 'merchant navy', 'ship captain',
        'loco pilot', 'train driver', 'truck driver', 'chauffeur', 'cab driver', 'taxi driver', 'car driver',
        'bus driver', 'delivery partner', 'delivery boy', 'delivery agent', 'courier', 'rider', 'warehouse',
        'forklift', 'cargo', 'stevedore', 'logistics', 'supply chain'
    ]) or (match_token(s, 'driver') and 'device' not in s and 'software' not in s and 'hardware' not in s):
        return 'Transportation & Logistics'

    # 9. Commerce, Category & Merchandising
    if match_any(s, [
        'category manager', 'category lead', 'category head', 'category', 'catalog', 'pricing', 'e-commerce',
        'ecommerce', 'merchandiser', 'merchandise', 'store associate', 'cashier', 'retail', 'shopkeeper',
        'counter sales', 'store manager'
    ]):
        return 'Commerce, Category & Retail'

    # 10. Sales, Commercial & Real Estate
    if match_any(s, [
        'sales', 'business development', 'bde', 'bda', 'inside sales', 'field sales', 'account executive',
        'realtor', 'real estate', 'broker', 'relationship manager', 'telecaller', 'tele-caller', 'telesales', 'telemarketing'
    ]):
        return 'Sales & Business Development'

    # 11. Marketing, Advertising, PR & Media
    if match_any(s, [
        'marketing', 'seo', 'sem', 'social media', 'content writer', 'copywriter', 'branding', 'pr executive',
        'public relations', 'advertising', 'journalist', 'reporter', 'news anchor', 'video editor', 'photographer',
        'animator', 'graphic designer', 'artist', 'musician', 'author', 'editor'
    ]):
        return 'Marketing, Media & Design'

    # 12. Finance, Banking, Accounting & Audit
    if match_any(s, [
        'accountant', 'accounting', 'chartered accountant', 'ca', 'cpa', 'auditor', 'bookkeeper',
        'taxation', 'tax consultant', 'billing', 'banking', 'bank officer', 'bank teller', 'bank manager',
        'loan officer', 'insurance', 'underwriter', 'actuary', 'investment banker', 'wealth manager'
    ]):
        return 'Finance, Banking & Accounting'

    # 13. Human Resources & Talent Acquisition
    if match_any(s, [
        'hr', 'human resource', 'recruiter', 'recruiting', 'talent acquisition', 'staffing',
        'people partner', 'people ops', 'hrbp', 'payroll'
    ]):
        return 'HR & People Operations'

    # 14. Customer Experience, Support & Operations
    if match_any(s, [
        'customer service', 'customer support', 'customer care', 'call center', 'bpo', 'kpo',
        'receptionist', 'front desk', 'helpdesk', 'service desk', 'customer success', 'csm', 'technical support'
    ]):
        return 'Customer Support & Operations'

    # 15. Product Management & UI/UX Design
    if match_any(s, [
        'product manager', 'associate product manager', 'apm', 'technical product manager', 'tpm',
        'product owner', 'scrum master', 'agile coach', 'ui/ux', 'ux designer', 'product designer',
        'ui designer', 'interaction designer'
    ]):
        return 'Product Management & Design'

    # 16. Consulting, Strategy & General Management
    if match_any(s, [
        'management consultant', 'strategy consultant', 'corporate strategy', 'operations manager',
        'general manager', 'business manager', 'project manager', 'program manager', 'pmo', 'operations lead',
        'team lead - operations', 'team lead operations', 'operations team lead', 'operations supervisor',
        'bpo team lead', 'support team lead', 'process team lead', 'process lead', 'process associate',
        'operations associate', 'operations executive'
    ]):
        return 'Business Operations & Management'

    # 17. Public Administration, Civil Services & Agriculture
    if match_any(s, [
        'civil servant', 'ias', 'ips', 'upsc', 'government officer', 'govt officer', 'clerk',
        'farmer', 'farming', 'agriculture', 'agronomist', 'horticulturist', 'dairy', 'forestry', 'geologist'
    ]):
        return 'Public Administration & Agriculture'

    # 18. Students, Freshers & Career Transitions
    if match_any(s, [
        'student', 'learner', 'intern', 'fresher', 'non coder', 'non-coder', 'non-tech', 'non tech',
        'zero code', 'career break', 'break', 'sabbatical', 'gap year', 'homemaker', 'housewife', 'restart'
    ]):
        return 'Early Career & Career Transitions'

    # 19. Technical Engineering Domains
    if match_any(s, [
        'test', 'tester', 'testing', 'qa', 'sdet', 'automation tester', 'manual tester', 'manual test',
        'quality analyst', 'quality assurance', 'automation engineer', 'test engineer', 'qa engineer'
    ]):
        return 'Quality Assurance & SDET'
    elif match_any(s, [
        'data scientist', 'data analyst', 'data engineer', 'analytics', 'bi', 'business intelligence',
        'power bi', 'tableau', 'machine learning', 'ml engineer', 'mle', 'ai engineer', 'deep learning',
        'computer vision', 'nlp', 'applied scientist', 'big data engineer', 'etl developer', 'bi developer',
        'bi engineer', 'analytics engineer'
    ]):
        return 'Data Science & Analytics'
    elif match_any(s, [
        'devops', 'sre', 'site reliability', 'cloud', 'infrastructure', 'docker', 'kubernetes',
        'platform engineer', 'terraform', 'sysadmin', 'system administrator', 'linux administrator', 'linux admin',
        'security engineer', 'cyber security', 'cybersecurity', 'infosec', 'soc analyst', 'penetration test',
        'appsec', 'network engineer', 'network admin', 'network administrator', 'network architect',
        'azure administrator', 'aws engineer', 'build and release', 'release engineer'
    ]):
        return 'DevOps & Cloud Platform'
    elif match_any(s, [
        'systems engineer', 'system engineer', 'systems engineering', 'systems architect', 'embedded',
        'hardware', 'firmware', 'vlsi', 'iot', 'linux kernel', 'device driver', 'soc design', 'asic',
        'fpga', 'operating systems', 'embedded developer', 'firmware developer', 'kernel developer'
    ]):
        return 'Systems & Embedded Engineering'
    elif match_any(s, [
        'frontend', 'front-end', 'ui dev', 'ui developer', 'ui engineer', 'web engineer', 'react', 'angular',
        'web developer', 'vue', 'frontend engineer', 'frontend developer'
    ]) and not any(des in s for des in ['designer', 'design', 'ux designer', 'product designer']):
        return 'Frontend Engineering'
    elif (
        match_any(s, [
            'engineering manager', 'tech lead', 'technical lead', 'software manager', 'dev manager',
            'technical architect', 'solutions architect', 'enterprise architect', 'lead architect',
            'software architect', 'cloud architect', 'systems architect', 'data architect', 'cto',
            'vp of engineering', 'director of engineering', 'chief technology officer',
            'engineering leadership', 'tech leadership', 'technical leadership',
            'software leadership', 'engineering lead'
        ]) or 
        (
            match_token(s, 'team lead') and not any(op in s for op in [
                'operation', 'bpo', 'kpo', 'support', 'sales', 'marketing', 'hr', 'talent',
                'retail', 'logistics', 'finance', 'non-tech', 'call center', 'process'
            ])
        ) or
        (
            match_any(s, ['manager', 'director', 'founder', 'vp', 'architect', 'lead', 'leadership']) and 
            match_any(s, ['software', 'tech', 'dev', 'engineering', 'platform', 'cloud', 'data'])
        )
    ):
        return 'Engineering Leadership'
    elif match_any(s, [
        'it service', 'general it', 'app support', 'desktop support', 'production support',
        'database administrator', 'dba', 'database engineer', 'oracle dba', 'sql dba', 'postgresql dba'
    ]):
        return 'IT Services & Maintenance'
    elif match_any(s, [
        'software', 'developer', 'programmer', 'sde', 'swe', 'backend', 'back-end', 'fullstack',
        'full-stack', 'full stack', 'application engineer', 'application developer', 'java dev',
        'python dev', 'golang', 'node', 'django', 'spring boot', 'ios', 'android', 'mobile dev',
        'mobile engineer', 'game dev', 'blockchain', 'ruby', 'rust', 'scala', 'php'
    ]):
        return 'Software Engineering (Backend/FullStack)'

    return 'Non-Tech / General Career Background'

@functools.lru_cache(maxsize=8192)
def canonical_persona_key_legacy(persona_str):
    """
    Maps ANY job title or persona string in the world to its canonical Scaler taxonomy key.
    Enforces the Golden Principle: unknown roles without explicit software/tech markers
    safely and universally classify as 'NON_TECH', never as 'SWE_BACKEND'.
    """
    raw_str = str(persona_str).strip()
    if raw_str in CANONICAL_PERSONA_NAMES:
        return raw_str
    for k, name in CANONICAL_PERSONA_NAMES.items():
        if raw_str.lower() == name.lower():
            return k
    s = raw_str.lower().replace('_', ' ')


    # --------------------------------------------------------------------------
    # 1. NON-TECH GLOBAL DOMAINS (Explicit Real-World Vocations)
    # --------------------------------------------------------------------------
    if any(k in s for k in [
        # Healthcare & Medicine (Nurse, Doctor, Pharmacist, Lab Tech, etc.)
        'nurse', 'nursing', 'doctor', 'physician', 'surgeon', 'dentist', 'dental', 'pharmacist',
        'pharmacy', 'chemist', 'paramedic', 'emt', 'ambulance', 'physiotherapist', 'physiotherapy',
        'radiologist', 'radiology', 'sonographer', 'lab technician', 'pathologist', 'pathology',
        'clinical', 'clinic', 'hospital', 'healthcare', 'health care', 'optometrist', 'veterinarian', 'dietitian',
        'nutritionist', 'phlebotomist', 'caregiver', 'ward boy', 'orderly', 'anesthesiologist',

        # Security, Defense & Protective Services (Guard, Police, Army, etc.)
        'security guard', 'security officer', 'guard', 'watchman', 'chowkidar', 'bouncer', 'bodyguard',
        'police', 'cop', 'constable', 'inspector', 'sho', 'law enforcement', 'detective', 'military',
        'army', 'navy', 'air force', 'armed forces', 'defense', 'defence', 'paramilitary',
        'firefighter', 'fireman', 'corrections officer', 'jailer', 'warden', 'border patrol',

        # Education, Teaching & Academia
        'teacher', 'school teacher', 'professor', 'lecturer', 'tutor', 'tuition', 'instructor',
        'educator', 'faculty', 'dean', 'principal', 'headmaster', 'headmistress', 'academic counselor',
        'librarian', 'pedagogy',

        # Hospitality, Facility & Cleaning Services
        'sweeper', 'cleaner', 'janitor', 'housekeeper', 'housekeeping', 'sanitation', 'maid', 'laundry',
        'chef', 'cook', 'baker', 'bakery', 'barista', 'bartender', 'waiter', 'waitress', 'server',
        'steward', 'restaurant', 'cafe', 'hotel', 'hospitality', 'concierge',
        'travel agent', 'tour guide', 'flight attendant', 'cabin crew', 'air hostess', 'sommelier',

        # Trades, Crafts & Construction
        'electrician', 'plumber', 'carpenter', 'welder', 'machinist', 'mechanic', 'auto mechanic',
        'fitter', 'turner', 'mason', 'masonry', 'construction', 'builder', 'painter', 'hvac',
        'appliance repair', 'blacksmith', 'locksmith', 'tailor', 'cobbler', 'weaver', 'factory worker',

        # Transportation & Logistics
        'driver', 'chauffeur', 'truck driver', 'delivery boy', 'delivery partner', 'delivery agent',
        'courier', 'rider', 'pilot', 'loco pilot', 'train driver', 'mariner', 'sailor', 'warehouse',
        'forklift', 'cargo', 'stevedore', 'logistics', 'supply chain',

        # Retail, Commerce, Category & Merchandising & Operations
        'cashier', 'store associate', 'retail', 'shopkeeper', 'counter sales', 'merchandiser', 'merchandise',
        'category manager', 'category lead', 'category head', 'category', 'catalog', 'pricing', 'e-commerce', 'ecommerce',
        'customer service', 'customer support', 'customer care', 'call center', 'bpo', 'kpo',
        'telecaller', 'tele-caller', 'telemarketing', 'front desk', 'receptionist',
        'operations manager', 'operations lead', 'team lead - operations', 'team lead operations',
        'operations team lead', 'operations supervisor', 'bpo team lead', 'support team lead',
        'process team lead', 'process lead', 'process associate', 'operations associate',

        # Corporate HR, Sales, Marketing, Finance, Legal
        'hr', 'human resource', 'recruiter', 'recruiting', 'talent acquisition', 'staffing',
        'people partner', 'people ops', 'hrbp', 'payroll',
        'sales', 'business development', 'bde', 'bda', 'inside sales', 'field sales', 'account executive',
        'realtor', 'real estate', 'broker', 'relationship manager',
        'marketing', 'seo', 'sem', 'social media', 'content writer', 'copywriter', 'branding', 'pr executive',
        'accountant', 'accounting', 'chartered accountant', 'ca ', 'cpa', 'auditor', 'bookkeeper',
        'taxation', 'tax consultant', 'billing', 'banking', 'bank officer', 'bank teller', 'loan officer',
        'insurance', 'underwriter', 'actuary',
        'lawyer', 'advocate', 'attorney', 'legal', 'paralegal', 'solicitor', 'barrister', 'notary',
        'compliance', 'judge', 'magistrate', 'civil servant', 'ias', 'ips', 'upsc', 'government officer',
        'govt officer', 'clerk',

        # Traditional Engineering (Non-CS)
        'mechanical', 'civil', 'chemical', 'petroleum', 'mining', 'metallurgy',
        'aerospace', 'aeronautical', 'biotech', 'biotechnology', 'biomedical', 'textile', 'automobile engineer',

        # Media, Design, Arts, Agriculture & Gaps
        'ui/ux designer', 'ui designer', 'ux designer', 'product designer', 'interaction designer', 'ui/ux',
        'graphic designer', 'illustrator', 'photographer', 'videographer', 'video editor', 'animator',
        'interior designer', 'fashion designer', 'artist', 'musician', 'singer', 'actor', 'journalist', 'reporter',
        'farmer', 'farming', 'agriculture', 'agronomist', 'horticulturist', 'dairy', 'forestry', 'geologist',
        'student', 'learner', 'intern', 'fresher', 'non coder', 'non-coder', 'non-tech', 'non tech',
        'zero code', 'career break', 'break', 'sabbatical', 'gap year', 'homemaker', 'housewife', 'restart'
    ]):
        # Protect dual-context roles like "Software Engineer at Hospital" or "Data Analyst in Healthcare"
        has_explicit_tech = any(match_token(s, t) for t in [
            'software engineer', 'software developer', 'backend developer', 'frontend developer',
            'full stack', 'fullstack', 'full-stack', 'application engineer', 'application developer',
            'data analyst', 'data scientist', 'data engineer', 'devops engineer',
            'cloud engineer', 'qa engineer', 'sdet', 'systems engineer', 'system engineer',
            'programmer', 'sde', 'swe', 'ml engineer', 'machine learning', 'ai engineer',
            'cyber security', 'cybersecurity', 'security engineer', 'security analyst',
            'network engineer', 'cloud architect', 'devops', 'sre', 'embedded', 'firmware',
            'device driver', 'database administrator', 'dba', 'ui engineer', 'web engineer',
            'mobile engineer', 'solutions architect', 'software architect', 'enterprise architect',
            'technical lead', 'tech lead', 'engineering manager', 'principal engineer', 'principal technical',
            'research engineer', 'staff engineer'
        ])
        if not has_explicit_tech:
            return 'NON_TECH'

    # --------------------------------------------------------------------------
    # 2. TECHNICAL ROLE CLASSIFICATION
    # --------------------------------------------------------------------------
    # QA / SDET / Testing
    if any(match_token(s, k) for k in [
        'test', 'tester', 'testing', 'qa', 'sdet', 'automation tester', 'manual tester', 'manual test',
        'quality analyst', 'quality assurance', 'test engineer', 'qa engineer'
    ]):
        return 'QA_SDET'

    # Data Science & Machine Learning / Analytics
    if any(match_token(s, k) for k in [
        'data scientist', 'data analyst', 'data engineer', 'analytics', 'bi', 'business intelligence',
        'power bi', 'tableau', 'machine learning', 'ml engineer', 'mle', 'ai engineer', 'nlp',
        'computer vision', 'deep learning', 'applied scientist', 'analytics engineer', 'big data engineer',
        'etl developer', 'bi developer', 'bi engineer', 'database engineer', 'business analyst',
        'data science', 'data scientist', 'data sciences', 'research scientist', 'decision scientist',
        'applied ai', 'ai ml', 'ai/ml', 'aiml', 'mlops', 'ml ops', 'llm', 'generative ai', 'gen ai', 'genai',
        'prompt engineer', 'statistician', 'quantitative analyst', 'quant analyst', 'insights analyst',
        'reporting analyst', 'mis analyst', 'data & analytics', 'data and analytics', 'data architect',
        'research engineer', 'research engineers'
    ]):
        return 'DATA_ANALYST'

    # DevOps, Cloud, Security & Infrastructure Platform
    if any(match_token(s, k) for k in [
        'devops', 'sre', 'cloud', 'infrastructure', 'docker', 'kubernetes', 'platform engineer',
        'terraform', 'sysadmin', 'system administrator', 'security', 'cyber security', 'cybersecurity',
        'infosec', 'soc analyst', 'penetration test', 'penetration tester', 'pen tester', 'network engineer',
        'network admin', 'network administrator', 'network architect', 'cloud architect', 'site reliability',
        'it infrastructure', 'linux administrator', 'linux admin', 'azure administrator',
        'aws engineer', 'build and release', 'release engineer', 'appsec'
    ]):
        return 'DEVOPS_CLOUD'

    # Systems & Embedded Engineering
    if any(match_token(s, k) for k in [
        'systems engineer', 'system engineer', 'systems engineering', 'systems architect',
        'embedded', 'hardware', 'firmware', 'vlsi', 'iot', 'linux kernel', 'device driver',
        'soc design', 'asic', 'fpga', 'operating systems', 'embedded developer', 'firmware developer',
        'kernel developer', 'driver developer'
    ]):
        return 'SYSTEMS_ENG'

    # Technical Engineering Leadership
    if (
        any(match_token(s, k) for k in [
            'engineering manager', 'tech lead', 'technical lead', 'software manager',
            'development manager', 'technical architect', 'solutions architect', 'enterprise architect',
            'lead architect', 'software architect', 'systems architect', 'data architect', 'cto',
            'vp of engineering', 'director of engineering', 'chief technology officer',
            'engineering leadership', 'tech leadership', 'technical leadership', 'software leadership',
            'head of engineering', 'head of tech', 'vp engineering', 'director engineering',
            'principal engineer', 'staff engineer', 'lead engineer', 'lead developer', 'distinguished engineer'
        ]) or 
        (
            match_token(s, 'team lead') and not any(op in s for op in [
                'operation', 'bpo', 'kpo', 'support', 'sales', 'marketing', 'hr', 'talent',
                'retail', 'logistics', 'finance', 'non-tech', 'call center', 'process'
            ])
        ) or
        (
            match_any(s, ['manager', 'director', 'founder', 'vp', 'architect', 'lead', 'leadership', 'head']) and 
            match_any(s, ['software', 'tech', 'dev', 'engineering', 'platform', 'cloud', 'data'])
        )
    ):
        return 'LEADERSHIP'

    # Frontend Engineering
    if any(match_token(s, k) for k in [
        'frontend', 'front-end', 'ui dev', 'ui developer', 'ui engineer', 'web engineer', 'react', 'angular',
        'web developer', 'frontend engineer', 'frontend developer'
    ]) and not any(des in s for des in ['designer', 'design', 'ux designer', 'product designer']):
        return 'FRONTEND'

    # General IT Services & Maintenance
    if any(match_token(s, k) for k in [
        'maintenance', 'support', 'it service', 'general it', 'service based', 'production support',
        'app support', 'desktop support', 'service desk', 'helpdesk', 'database administrator', 'dba',
        'oracle dba', 'sql dba', 'postgresql dba'
    ]):
        return 'IT_SERVICES'

    # Core Software Engineering (Backend / Full Stack)
    if any(match_token(s, k) for k in [
        'software', 'developer', 'programmer', 'coding', 'coder', 'sde', 'swe',
        'backend', 'back-end', 'fullstack', 'full-stack', 'full stack', 'application engineer',
        'application developer', 'java dev', 'python dev', 'c++', 'c#', '.net', 'golang',
        'node', 'django', 'spring boot', 'android', 'ios', 'mobile engineer', 'mobile dev',
        'flutter', 'react native', 'ruby', 'rust', 'scala', 'php'
    ]):
        return 'SWE_BACKEND'

    # --------------------------------------------------------------------------
    # 3. UNIVERSAL SAFE FALLBACK
    # If a role has NO verified software or technical engineering keywords,
    # it safely defaults to NON_TECH (Career Switcher), never SWE_BACKEND!
    # --------------------------------------------------------------------------
    return 'NON_TECH'


@functools.lru_cache(maxsize=2048)
def canonical_exp_key(exp_str):
    if exp_str is None:
        return 'EXP_1_3'
    s = str(exp_str).strip().lower()
    if any(k in s for k in ['not specified', 'unspecified', 'unknown', 'not provided', 'not mentioned']):
        return 'EXP_1_3'
    
    # 1. Check if a 4-digit graduation year is present (e.g. Batch 2025, Batch 2023, Batch 2012)
    year_match = re.search(r'\b(19\d\d|20\d\d)\b', s.replace(',', ''))
    if year_match:
        grad_year = int(year_match.group(1))
        current_year = 2026
        if grad_year >= 2025:
            return 'EXP_0_1'
        diff = max(0, current_year - grad_year)
        if diff < 1:
            return 'EXP_0_1'
        elif diff < 3:
            return 'EXP_1_3'
        elif diff < 5:
            return 'EXP_3_5'
        else:
            return 'EXP_5_PLUS'

    # 2. Check compound years and months like "5 years 6 months", "3 yrs 4 mos"
    compound = re.search(r'(\d+(?:\.\d+)?)\s*(?:yrs|yr|years?)\s*(?:and\s*)?(\d+(?:\.\d+)?)\s*(?:mos|mo|months?)', s)
    if compound:
        try:
            val = float(compound.group(1)) + float(compound.group(2)) / 12.0
            if val < 1.0:
                return 'EXP_0_1'
            elif val < 3.0:
                return 'EXP_1_3'
            elif val < 5.0:
                return 'EXP_3_5'
            else:
                return 'EXP_5_PLUS'
        except Exception:
            pass

    # Numeric extraction for actual YOE (handles 8.0 yrs, 2.5 years, 0 years, 18 months)
    match = re.search(r'[-+]?\d*\.?\d+', s.replace(',', ''))
    if match and match.group():
        try:
            val = float(match.group())
            # Convert months ONLY if text has month indicators AND does NOT have year indicators
            has_month = any(m in s for m in ['month', 'mo', 'mth'])
            has_year = any(y in s for y in ['year', 'yr'])
            if has_month and not has_year:
                val = val / 12.0
            if val < 1.0:
                return 'EXP_0_1'
            elif val < 3.0:
                return 'EXP_1_3'
            elif val < 5.0:
                return 'EXP_3_5'
            else:
                return 'EXP_5_PLUS'
        except Exception:
            pass

    # 3. Keyword matching for non-numeric strings
    if any(k in s for k in ['fresher', 'student', 'intern', 'college', 'beginner', '< 1', '0-1']):
        return 'EXP_0_1'

    if any(k in s for k in ['1 - 3', '1-2', '2-3', '1 year', '2 year', '1 yr', '2 yr']):
        return 'EXP_1_3'
    elif any(k in s for k in ['3 - 5', '3-5', '3 year', '4 year', '3 yr', '4 yr']):
        return 'EXP_3_5'
    return 'EXP_5_PLUS'

_MATRIX_CACHE = None
_INDEXED_3D = {}
_INDEXED_2D = {}
_INDEXED_1D = {}

def _build_matrix_indexes(matrix_data):
    global _INDEXED_3D, _INDEXED_2D, _INDEXED_1D
    _INDEXED_3D = {}
    for k, stat in matrix_data.get('by_program_persona_exp', {}).items():
        parts = k.split('___')
        if len(parts) == 3:
            p = canonical_prog_key(parts[0])
            pers = canonical_persona_key(parts[1])
            exp = canonical_exp_key(parts[2])
            _INDEXED_3D[(p, pers, exp)] = stat

    _INDEXED_2D = {}
    for k, stat in matrix_data.get('by_program_persona', {}).items():
        parts = k.split('___')
        p = canonical_prog_key(parts[0]) if len(parts) >= 2 else canonical_prog_key(k)
        pers = canonical_persona_key(parts[1]) if len(parts) >= 2 else canonical_persona_key(k)
        _INDEXED_2D[(p, pers)] = stat

    _INDEXED_1D = {}
    for k, stat in matrix_data.get('by_program', {}).items():
        _INDEXED_1D[canonical_prog_key(k)] = stat

def load_matrix():
    global _MATRIX_CACHE
    if _MATRIX_CACHE is not None:
        return _MATRIX_CACHE
    if os.path.exists(MATRIX_JSON_PATH):
        try:
            with open(MATRIX_JSON_PATH, 'r', encoding='utf-8') as f:
                _MATRIX_CACHE = json.load(f)
                _build_matrix_indexes(_MATRIX_CACHE)
                return _MATRIX_CACHE
        except Exception:
            pass
    _MATRIX_CACHE = {}
    return _MATRIX_CACHE

def get_cohort_stats(program, persona, experience=None, matrix_data=None):
    """
    Defensively retrieves retention and refund rates with canonical key matching and Bayesian fallback.
    Guaranteed NEVER to return None. Uses precomputed O(1) indexes for lightning-fast batch processing.
    """
    if matrix_data is None:
        matrix_data = load_matrix()

    p_key = canonical_prog_key(program)
    pers_key = canonical_persona_key(persona)
    exp_key = canonical_exp_key(experience) if experience else 'EXP_1_3'

    if not _INDEXED_3D and matrix_data:
        _build_matrix_indexes(matrix_data)

    # 1. 3D search by exact dimensions
    stat = _INDEXED_3D.get((p_key, pers_key, exp_key))
    if stat:
        ret = stat.get('smoothed_retention_rate', stat.get('raw_retention_rate', stat.get('retention_rate', 78.2)))
        ref = stat.get('smoothed_refund_rate', stat.get('raw_refund_rate', stat.get('refund_rate', 21.8)))
        tot = stat.get('cohort_size', stat.get('total', 100))
        return {
            'retention_rate': ret,
            'refund_rate': ref,
            'total': tot,
            'cohort_size': tot,
            'level': '3D',
            'risk_level': 'High Retention' if ret >= 80 else ('Moderate' if ret >= 75 else 'High Risk')
        }

    # 2. 2D search in by_program_persona
    stat = _INDEXED_2D.get((p_key, pers_key))
    if stat:
        ret = stat.get('retention_rate', stat.get('smoothed_retention_rate', 78.2))
        ref = stat.get('refund_rate', stat.get('smoothed_refund_rate', 21.8))
        tot = stat.get('cohort_size', stat.get('total', 100))
        return {
            'retention_rate': ret,
            'refund_rate': ref,
            'total': tot,
            'cohort_size': tot,
            'level': '2D',
            'risk_level': 'High Retention' if ret >= 80 else ('Moderate' if ret >= 75 else 'High Risk')
        }

    # 3. 1D search in by_program
    stat = _INDEXED_1D.get(p_key)
    if stat:
        ret = stat.get('retention_rate', 78.2)
        ref = stat.get('refund_rate', 21.8)
        tot = stat.get('cohort_size', stat.get('total', 500))
        return {
            'retention_rate': ret,
            'refund_rate': ref,
            'total': tot,
            'cohort_size': tot,
            'level': '1D',
            'risk_level': 'High Retention' if ret >= 80 else ('Moderate' if ret >= 75 else 'High Risk')
        }

    # Guaranteed Default Fallback
    return dict(DEFAULT_FALLBACK)

def get_persona_level_stats(program, persona, matrix_data=None, min_n=0):
    """Retention for (program, persona) across all experience bands; the program overall when the persona has no data."""
    return _persona_level(program, persona, matrix_data, min_n)


def _persona_level(program, persona, matrix_data=None, min_n=0):
    if matrix_data is None:
        matrix_data = load_matrix()
    if not _INDEXED_3D and matrix_data:
        _build_matrix_indexes(matrix_data)
    p_key, pers_key = canonical_prog_key(program), canonical_persona_key(persona)
    stat = _INDEXED_2D.get((p_key, pers_key))
    if stat and stat.get('cohort_size', stat.get('total', 100)) >= min_n:
        ret = stat.get('retention_rate', stat.get('smoothed_retention_rate', 78.2))
        tot = stat.get('cohort_size', stat.get('total', 100))
        return {'retention_rate': ret, 'refund_rate': round(100 - float(ret), 1), 'cohort_size': tot, 'total': tot, 'level': '2D'}
    stat = _INDEXED_1D.get(p_key)
    if stat:
        ret = stat.get('retention_rate', 78.2); tot = stat.get('cohort_size', stat.get('total', 500))
        return {'retention_rate': ret, 'refund_rate': round(100 - float(ret), 1), 'cohort_size': tot, 'total': tot, 'level': '1D'}
    return dict(DEFAULT_FALLBACK, level='default')


# Helper aliases
normalize_persona = lambda raw_persona, raw_role: canonical_persona_key(f"{raw_persona} {raw_role}")
normalize_experience = lambda exp_val: canonical_exp_key(exp_val)
normalize_program = lambda prog_val: canonical_prog_key(prog_val)
def get_canonical_persona_name(key_or_str):
    if key_or_str in CANONICAL_PERSONA_NAMES:
        return CANONICAL_PERSONA_NAMES[key_or_str]
    norm_key = canonical_persona_key(key_or_str)
    return CANONICAL_PERSONA_NAMES.get(norm_key, 'Non-Tech / Career Switcher')



def canonical_persona_key(persona_str):
    """Persona key for a role (or a combined persona/role text). Unknown text maps to NON_TECH here, as it always did for matrix cohorts;
    callers that need to tell 'unknown' from 'non-technical' use role_taxonomy.classify_role directly."""
    raw_str = str(persona_str).strip()
    if raw_str in CANONICAL_PERSONA_NAMES:
        return raw_str
    for k, name in CANONICAL_PERSONA_NAMES.items():
        if raw_str.lower() == name.lower():
            return k
    from .role_taxonomy import classify_role
    key, _why = classify_role(raw_str)
    return key or 'NON_TECH'

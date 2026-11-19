import os
import io
import re
import pandas as pd
from .evaluator import evaluate_lead_profile

def find_col(df, candidates):
    cols_lower = {str(c).lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand in cols_lower:
            return cols_lower[cand]
    for cand in candidates:
        for c_lower, orig in cols_lower.items():
            # Avoid substring collisions: 'company' should not match 'company_type'
            if cand == 'company' and 'type' in c_lower:
                continue
            # 'name' as substring must NOT match 'first_name', 'last_name', 'company_name', 'event_name', etc.
            if cand == 'name' and any(sub in c_lower for sub in ['first', 'last', 'org', 'company', 'event', 'course', 'full', 'student', 'lead', 'team']):
                continue
            if cand == 'role' and any(sub in c_lower for sub in ['owner', 'team']):
                continue
            if cand == 'id' and c_lower != 'id':
                continue
            if cand in c_lower:
                return orig
    return None

def _year_label(org, year):
    """The org year is the year the person joined their organisation. Only a college's year reads as a batch."""
    o = str(org or '').lower()
    if any(k in o for k in ('college', 'university', 'institute', 'school', 'campus', 'student', 'iit', 'nit ', 'iiit', 'polytechnic')):
        return f"Batch {year}"
    return f"since {year}"


def process_leads_dataframe(df, include_export_df=False, index_offset=0):
    """
    Defensively processes an arbitrary leads dataframe, evaluates each lead,
    and returns a list of evaluated records plus an enriched exportable dataframe.
    Optimized for high-throughput batch evaluation with low memory footprint.
    """
    col_lead_id = find_col(df, ['lead_id', 'lead id', 'leadid', 'lsq_id', 'prospect_id', 'candidate_id', 'crm_lead_id', 'id'])
    col_first_name = find_col(df, ['first_name', 'first name', 'firstname', 'fname', 'given_name', 'candidate_first_name', 'lead_first_name', 'contact_first_name'])
    col_last_name = find_col(df, ['last_name', 'last name', 'lastname', 'lname', 'surname', 'family_name', 'candidate_last_name', 'lead_last_name', 'contact_last_name'])
    col_full_name = find_col(df, ['full_name', 'fullname', 'candidate_name', 'lead_name', 'student_name', 'contact_name', 'name'])
    col_email = find_col(df, ['email', 'email id', 'lead email', 'contact email'])
    col_phone = find_col(df, ['phone', 'contact', 'mobile', 'phone number', 'mobile number'])
    col_role = find_col(df, ['role', 'current role', 'designation', 'job title', 'title', 'current designation', 'profile'])
    col_company_type = find_col(df, ['company_type', 'company type', 'org type', 'current company type', 'industry', 'sector'])
    col_prev_org = find_col(df, ['orgname', 'organization', 'previous org name', 'employer', 'company_name', 'company', 'prev org', 'current company'])
    col_prev_year = find_col(df, ['orgyear', 'org year', 'previous org year', 'graduation_year', 'passout_year', 'batch_year', 'tenure'])
    col_exp = find_col(df, ['experience', 'yoe', 'total experience', 'work experience', 'total work experience', 'years of experience', 'exp'])
    col_event = find_col(df, ['event_name', 'event', 'webinar', 'course_name', 'activity', 'masterclass'])
    col_prog = find_col(df, ['program_type', 'which_bda_team', 'program', 'inbound program', 'intake program', 'current program', 'course', 'enquiry program', 'applied program'])
    col_attended = find_col(df, ['attended', 'is_attended', 'webinar_attended', 'live_attended', 'mng attended live', '1 live attendance'])
    col_attended_at = find_col(df, ['attended_at', 'attendance_time', 'attended_date'])
    col_duration = find_col(df, ['minutes_in_event', 'duration', 'watch_time', 'time_spent', 'minutes_spent'])
    col_event_rank = find_col(df, ['event_rank_registraion', 'event_rank_registration', 'event_rank'])
    col_utm_source = find_col(df, ['utm_source', 'source', 'lead_source', 'marketing_source'])
    col_utm_medium = find_col(df, ['utm_medium', 'medium'])
    col_utm_campaign = find_col(df, ['utm_campaign', 'campaign'])
    col_landing = find_col(df, ['landing_page_url', 'landing_url', 'url', 'page_url'])
    col_platform = find_col(df, ['platform', 'device', 'device_type'])
    col_test_launched = find_col(df, ['test_launched_flag', 'diagnostic set status', 'diagnostic sat status', 'attempted_set', 'attempted_sat', 'attempted set', 'attempted sat', 'set_attempted', 'sat_attempted', 'test_launched'])
    col_test_passed = find_col(df, ['test_passed_flag', 'test_passed', 'set_passed', 'sat_passed'])
    col_lead_score = find_col(df, ['lead_score', 'score', 'activity_score', 'lsq_score'])
    col_stage = find_col(df, ['current_lead_stage', 'lead_stage', 'stage', 'last_lead_stage'])
    col_country = find_col(df, ['country_type', 'country', 'region', 'entity'])
    col_team = find_col(df, ['which_bda_team'])
    col_event_type = find_col(df, ['event_type'])
    col_prog_type = find_col(df, ['program_type'])
    col_signup = find_col(df, ['signed_up_date', 'signup_date', 'created_at', 'lead_created_at', 'registration_date1', 'registration_date', 'onboarding date'])
    col_edu = find_col(df, ['education', 'degree', 'qualification', 'highest_qualification', 'stream', 'branch', 'graduation', 'college_degree', 'course_degree', 'academic_qualification', 'highest qualification', 'college_name'])
    col_sat_score = find_col(df, ['diagnostic set score', 'diagnostic sat score', 'set_score', 'sat_score', 'set_marks', 'sat_marks', 'test_score', 'coding_test_score', 'diagnostic_score', 'assessment_score', 'test_marks', 'set_result', 'sat_result'])

    evaluated_records = []
    enriched_rows = []
    import datetime
    CURRENT_YEAR = datetime.datetime.now().year

    raw_records = df.to_dict('records')
    for idx, row in enumerate(raw_records):
        # A lead is identified ONLY by real source data: its lead id or its email. Rows with neither are skipped,
        # because inventing an identifier would create fictitious leads.
        _em = str(row[col_email]).strip() if col_email and pd.notna(row[col_email]) else ""
        _lid = str(row[col_lead_id]).strip() if col_lead_id and pd.notna(row[col_lead_id]) else ""
        if _em.lower() in ('', 'nan', 'none', 'null') and _lid.lower() in ('', 'nan', 'none', 'null', 'n/a'):
            continue

        # Phone extraction first for fallback naming
        raw_phone = row[col_phone] if col_phone and pd.notna(row[col_phone]) else "N/A"
        if isinstance(raw_phone, float) and raw_phone.is_integer():
            cand_phone = str(int(raw_phone))
        else:
            cand_phone = str(raw_phone).replace('.0', '').strip()

        # 1. Candidate Name (supporting split first/last name, full name, or phone/email fallback)
        fname_val = str(row[col_first_name]).strip() if col_first_name and pd.notna(row[col_first_name]) else ""
        lname_val = str(row[col_last_name]).strip() if col_last_name and pd.notna(row[col_last_name]) else ""
        if fname_val.lower() in ['nan', 'none', 'null']: fname_val = ""
        if lname_val.lower() in ['nan', 'none', 'null']: lname_val = ""

        split_parts = [p for p in [fname_val, lname_val] if p]
        split_name = " ".join(split_parts).strip()

        full_val = str(row[col_full_name]).strip() if col_full_name and pd.notna(row[col_full_name]) else ""
        if full_val.lower() in ['nan', 'none', 'null']: full_val = ""

        # Prioritize full_name if available; otherwise split_name
        raw_name = full_val if full_val else split_name

        # Use the name exactly as stored in the source. If it is missing or clearly a system value (hash / digits),
        # leave it empty rather than guessing one from the email or phone number.
        has_hash = ('_' in raw_name) or bool(re.match(r'^\d+$', raw_name)) or (len(re.findall(r'[a-f0-9]{8,}', raw_name)) > 0)
        cand_name = "" if (not raw_name or has_hash) else raw_name

        cand_email = str(row[col_email]).strip() if col_email and pd.notna(row[col_email]) else ""

        # 2. Organization & Company Type
        raw_org = str(row[col_prev_org]).strip() if col_prev_org and pd.notna(row[col_prev_org]) else ""
        if raw_org.lower() in ['not applicable', 'not applicable account', 'nan', 'none', '']:
            cand_org = "Independent / Transitioning"
        else:
            cand_org = raw_org

        raw_comp_type = str(row[col_company_type]).strip() if col_company_type and pd.notna(row[col_company_type]) else ""
        if raw_comp_type.lower() in ['not applicable', 'nan', 'none', '']:
            cand_comp_type = "IT Services / Technology"
        else:
            cand_comp_type = raw_comp_type

        # 3. Graduation / Passout Year
        raw_year = row[col_prev_year] if col_prev_year and pd.notna(row[col_prev_year]) else None
        grad_year = None
        if raw_year is not None:
            m_yr = re.search(r'(19\d\d|20\d\d)', str(raw_year).replace(',', ''))
            if m_yr:
                grad_year = int(m_yr.group(1))

        # Track quality flags for missing data fallbacks
        data_quality_flags = []

        # Event / Masterclass signal
        event_str = str(row[col_event]).strip() if col_event and pd.notna(row[col_event]) else ""

        # 4. Role Extraction & Cross-Signal Inference
        raw_role = str(row[col_role]).strip() if col_role and pd.notna(row[col_role]) else ""
        if raw_role.lower() in ['nan', 'none', 'null', '', '-']:
            raw_role = ""

        # Cross-signal role inference if role is missing
        if not raw_role:
            combined_role_hints = f"{cand_comp_type} {event_str}".lower()
            if any(k in combined_role_hints for k in ['data_science', 'machine learning', 'data science', 'dsml', 'data analyst', 'analytics']):
                raw_role = "Data Analyst / Scientist (Inferred)"
                data_quality_flags.append("role_inferred")
            elif any(k in combined_role_hints for k in ['devops', 'cloud', 'kubernetes', 'docker', 'sre', 'platform']):
                raw_role = "DevOps / Systems Engineer (Inferred)"
                data_quality_flags.append("role_inferred")
            elif any(k in combined_role_hints for k in ['fde', 'forward deployed', 'solutions engineer']):
                raw_role = "Solutions / Forward Deployed Engineer (Inferred)"
                data_quality_flags.append("role_inferred")
            elif any(k in combined_role_hints for k in ['agentic', 'ai agent', 'genai', 'llm']):
                raw_role = "AI / ML Engineer (Inferred)"
                data_quality_flags.append("role_inferred")

        # 5. Experience Ingestion & Fallback Logic
        raw_exp = row[col_exp] if col_exp and pd.notna(row[col_exp]) else None
        exp_years = None
        exp_display = ""

        if raw_exp is not None:
            raw_exp_str = str(raw_exp).lower().replace(',', '')
            # 1. Compound years and months e.g. "5 yrs 6 mos", "3 years 4 months"
            m_comp = re.search(r'(\d+(?:\.\d+)?)\s*(?:yrs|yr|years?)\s*(?:and\s*)?(\d+(?:\.\d+)?)\s*(?:mos|mo|months?)', raw_exp_str)
            if m_comp:
                try:
                    exp_years = round(float(m_comp.group(1)) + float(m_comp.group(2)) / 12.0, 1)
                    exp_display = f"{exp_years} yrs"
                except Exception:
                    pass
            else:
                m_exp = re.search(r'[-+]?\d*\.?\d+', raw_exp_str)
                if m_exp:
                    try:
                        num_val = float(m_exp.group())
                        has_month = any(m in raw_exp_str for m in ['month', 'mo', 'mth'])
                        has_year = any(y in raw_exp_str for y in ['year', 'yr'])
                        if num_val > 0:
                            # In Marketing MIS / CRM, numeric experience is typically logged in total months
                            # (multiples of 6, 12, 18, 24, 36, 48, 60, etc.)
                            if has_month and not has_year:
                                exp_years = round(num_val / 12.0, 1)
                                exp_display = f"{exp_years} yrs ({int(num_val)} mos)"
                            elif has_year and not has_month:
                                exp_years = num_val
                                exp_display = f"{num_val} yrs"
                            elif num_val >= 6.0 and num_val <= 480.0:
                                # When bare integer >= 6, it represents months in Marketing MIS
                                exp_years = round(num_val / 12.0, 1)
                                exp_display = f"{exp_years} yrs ({int(num_val)} mos)"
                            elif num_val > 480.0:
                                exp_years = 1.0
                                exp_display = "Not Specified"
                            else:
                                exp_years = num_val
                                exp_display = f"{num_val} yrs"
                        elif num_val == 0:
                            exp_years = 0.0
                    except Exception:
                        pass

        # If experience is 0 or missing, consult orgyear (graduation year), role, or event
        event_str = str(row[col_event]).strip() if col_event and pd.notna(row[col_event]) else ""
        is_beginner_event = any(k in event_str.lower() for k in ['beginner', 'college', 'foundation', 'starter', 'for beginners'])

        is_senior_role = any(k in raw_role.lower() for k in ['leadership', 'director', 'vp', 'manager', 'head of', 'architect', 'principal'])
        is_entry_role = any(k in raw_role.lower() for k in ['student', 'intern', 'learner', 'fresher', 'non coder', 'college'])

        if exp_years is None or exp_years == 0.0:
            if is_senior_role:
                if grad_year is not None and grad_year <= 2024:
                    inferred_yoe = max(7, CURRENT_YEAR - grad_year)
                    exp_years = float(inferred_yoe)
                    exp_display = f"{inferred_yoe} yrs ({_year_label(cand_org, grad_year)})"
                else:
                    exp_years = 7.0
                    exp_display = "7+ yrs (Senior Profile)"
                data_quality_flags.append("experience_inferred_from_title")
            elif is_entry_role:
                exp_years = 0.0
                exp_display = "Fresher (Entry-level Role)"
                data_quality_flags.append("experience_inferred_from_title")
            elif grad_year is not None:
                if grad_year >= 2025:
                    if cand_org not in ['Independent / Transitioning', 'College / University', 'Student'] and not any(k in cand_org.lower() for k in ['student', 'learner', 'college', 'university', 'campus']):
                        exp_years = 1.0
                        exp_display = f"Junior / Associate ({_year_label(cand_org, grad_year)})"
                    else:
                        exp_years = 0.0
                        exp_display = f"Fresher ({_year_label(cand_org, grad_year)})"
                        if not raw_role or raw_role.lower() in ['learner', 'other']:
                            raw_role = "College Student"
                else:
                    inferred_yoe = max(1, CURRENT_YEAR - grad_year)
                    exp_years = float(inferred_yoe)
                    exp_display = f"{inferred_yoe} yrs ({_year_label(cand_org, grad_year)})"
                data_quality_flags.append("experience_inferred_from_grad_year")
            elif cand_org not in ['Independent / Transitioning', 'College / University', 'Student'] and not any(k in cand_org.lower() for k in ['student', 'learner', 'college', 'university', 'campus']):
                exp_years = 2.0
                exp_display = "Not Specified (Inferred 1-2 yrs)"
                data_quality_flags.append("experience_not_specified")
            elif is_beginner_event:
                exp_years = 0.0
                exp_display = "Fresher / Learner"
                if not raw_role:
                    raw_role = "Learner / Transitioner"
                data_quality_flags.append("experience_inferred_from_event")
            elif raw_role and any(k in raw_role.lower() for k in ['lead', 'senior', 'staff']):
                exp_years = 6.0
                exp_display = "6+ yrs (Senior Profile)"
                data_quality_flags.append("experience_inferred_from_title")
            else:
                if raw_exp is not None and (raw_exp == 0 or str(raw_exp).strip() in ['0', '0.0']):
                    exp_years = 0.0
                    exp_display = "0 years (Fresher / Entry-Level)"
                else:
                    exp_years = 2.0
                    exp_display = "Not Specified (Inferred 1-2 yrs)"
                    data_quality_flags.append("experience_not_specified")

        if not raw_role:
            if exp_years == 0.0:
                raw_role = "College Student / Fresher"
            else:
                raw_role = "General Professional / Career Switcher"
            data_quality_flags.append("role_defaulted")

        # 6. Inbound Program Synthesis (event_name + program_type + role fallback)
        prog_str = str(row[col_prog]).strip() if col_prog and pd.notna(row[col_prog]) else ""
        combined_intent = f"{event_str} {prog_str}".lower()
        role_intent_hint = raw_role.lower()

        if any(k in combined_intent for k in ['agentic', 'agent memory', 'rag pipeline', 'ai agent', 'genai', 'ai_ml']):
            inbound_prog = "Program 4: AI & Machine Learning with Agentic AI"
        elif any(k in combined_intent for k in ['forward deployed', 'fde', 'solutions engineer']):
            inbound_prog = "Program 3: AI Forward Deployed Engineer (FDE)"
        elif any(k in combined_intent for k in ['docker', 'kubernetes', 'devops', 'cloud', 'platform engineer']):
            inbound_prog = "Program 5: DevOps, Cloud & AI Platform Engineering"
        elif any(k in combined_intent for k in ['data_science', 'machine learning', 'data science', 'dsml', 'data analyst']):
            inbound_prog = "Program 2: Modern Data Science & Machine Learning (DSML)"
        elif combined_intent.strip():
            inbound_prog = "Program 1: Software & AI Engineering (Scaler Academy)"
        else:
            # Event and Program empty -> cross-infer from Role
            if any(k in role_intent_hint for k in ['data', 'analyst', 'machine learning', 'dsml']):
                inbound_prog = "Program 2: Modern Data Science & Machine Learning (DSML)"
                data_quality_flags.append("intent_inferred_from_role")
            elif any(k in role_intent_hint for k in ['devops', 'cloud', 'sre', 'platform', 'infrastructure']):
                inbound_prog = "Program 5: DevOps, Cloud & AI Platform Engineering"
                data_quality_flags.append("intent_inferred_from_role")
            elif any(k in role_intent_hint for k in ['fde', 'forward deployed', 'solutions']):
                inbound_prog = "Program 3: AI Forward Deployed Engineer (FDE)"
                data_quality_flags.append("intent_inferred_from_role")
            elif any(k in role_intent_hint for k in ['agent', 'genai', 'llm']):
                inbound_prog = "Program 4: AI & Machine Learning with Agentic AI"
                data_quality_flags.append("intent_inferred_from_role")
            else:
                inbound_prog = "Program 1: Software & AI Engineering (Scaler Academy)"
                data_quality_flags.append("intent_defaulted_to_p1")

        # 7. Comprehensive Touchpoint Capture
        attended_val = row[col_attended] if col_attended and pd.notna(row[col_attended]) else None
        if attended_val is not None:
            try:
                is_att = int(float(str(attended_val).strip())) == 1
                attended_str = "Attended" if is_att else "Registered Only"
            except Exception:
                attended_str = str(attended_val)
        else:
            attended_str = "Registered Only"

        dur_val = row[col_duration] if col_duration and pd.notna(row[col_duration]) else None
        duration_str = f"{round(float(dur_val), 1)} mins" if dur_val is not None and str(dur_val).replace('.', '').isdigit() else ""

        sat_score_val = row[col_sat_score] if col_sat_score and pd.notna(row[col_sat_score]) else None
        test_val = row[col_test_launched] if col_test_launched and pd.notna(row[col_test_launched]) else None
        test_passed_val = row[col_test_passed] if col_test_passed and pd.notna(row[col_test_passed]) else None

        if sat_score_val is not None and str(sat_score_val).strip() not in ['', 'nan', 'none']:
            sat_score_clean = str(sat_score_val).replace('.0', '').strip()
            sat_score_display = f"{sat_score_clean}/100" if sat_score_clean.isdigit() and int(sat_score_clean) <= 100 else sat_score_clean
            sat_status = f"Score: {sat_score_display}"
        elif test_passed_val is not None and str(test_passed_val).strip() in ['1', '1.0', 'true', 'True']:
            sat_status = "SET Passed"
            sat_score_display = "Passed (Cleared)"
        elif test_val is not None and str(test_val).strip() in ['1', '1.0', 'true', 'True']:
            sat_status = "SET Attempted"
            sat_score_display = "Attempted (Evaluation Pending)"
        else:
            sat_status = "SET Not Attempted"
            sat_score_display = "Not Attempted"

        if 'sat' in str(sat_status).lower():
            sat_status = str(sat_status).replace('SAT', 'SET').replace('Sat', 'Set').replace('sat', 'set')

        src_val = str(row[col_utm_source]).strip() if col_utm_source and pd.notna(row[col_utm_source]) else ""
        med_val = str(row[col_utm_medium]).strip() if col_utm_medium and pd.notna(row[col_utm_medium]) else ""
        camp_val = str(row[col_utm_campaign]).strip() if col_utm_campaign and pd.notna(row[col_utm_campaign]) else ""
        channel_str = f"{src_val} / {med_val}".strip(" /") if (src_val or med_val) else "Not available"

        plat_val = str(row[col_platform]).strip() if col_platform and pd.notna(row[col_platform]) else "Not available"
        geo_val = str(row[col_country]).strip() if col_country and pd.notna(row[col_country]) else "Not available"
        signup_val = str(row[col_signup]).strip() if col_signup and pd.notna(row[col_signup]) else "Not available"
        landing_val = str(row[col_landing]).strip() if col_landing and pd.notna(row[col_landing]) else ""
        score_val = str(row[col_lead_score]).replace('.0', '') if col_lead_score and pd.notna(row[col_lead_score]) else "N/A"

        # Touchpoint 1-line summary for table glance
        if duration_str:
            key_touchpoint = f"{attended_str} ({duration_str}) - {event_str[:40]}" if event_str else f"{attended_str} ({duration_str})"
        elif event_str:
            key_touchpoint = f"{attended_str} - {event_str[:45]}"
        else:
            key_touchpoint = f"{channel_str} - Inbound Web"

        touchpoint_dict = {
            'summary': key_touchpoint,
            'event_name': event_str if event_str else "Direct Inbound Registration",
            'attended': attended_str,
            'duration': duration_str if duration_str else "N/A",
            'sat_status': sat_status,
            'sat_score': sat_score_display,
            'channel': channel_str,
            'campaign': camp_val if camp_val else "N/A",
            'platform': plat_val,
            'geography': geo_val,
            'signup_date': signup_val,
            'lead_score': score_val,
            'landing_page': landing_val if landing_val else "https://www.scaler.com"
        }

        cand_edu = str(row[col_edu]).strip() if col_edu and pd.notna(row[col_edu]) else "Graduated / Degree"
        if (not col_edu) or cand_edu.lower() in ['nan', 'none', 'null', ''] or (col_edu and pd.isna(row[col_edu])):
            cand_edu = "Graduated / Degree"
            # The source has no education value, so graduation is an ASSUMPTION, not data. Flag it.
            data_quality_flags.append("education_assumed_graduate")

        lead_dict = {
            'name': cand_name,
            'email': cand_email,
            'phone': cand_phone,
            'role': raw_role,
            'company type': ('' if raw_comp_type.lower() in ['not applicable', 'nan', 'none', ''] else cand_comp_type),   # a defaulted value must not look like source data
            'previous org name': cand_org,
            'previous org year': str(grad_year) if grad_year else "1-2 years",
            'experience': exp_display if exp_display else f"{exp_years} years",
            'education': cand_edu,
            'education_missing': 'education_assumed_graduate' in data_quality_flags,
            'sat_score': sat_score_display,
            'sat_status': sat_status,
            'program': inbound_prog,
            # the lead's raw CRM values, for the learned program ranking
            'crm': {k: (row[c] if c and pd.notna(row[c]) else None) for k, c in (
                ('program_type', col_prog_type or col_prog), ('which_bda_team', col_team), ('event_name', col_event), ('event_type', col_event_type),
                ('landing_page_url', col_landing), ('utm_source', col_utm_source), ('country_type', col_country), ('orgname', col_prev_org),
                ('orgyear', col_prev_year), ('test_passed_flag', col_test_passed), ('company_type', col_company_type), ('role', col_role),
                ('attended', col_attended), ('minutes_in_event', col_duration), ('event_rank_registraion', col_event_rank))},
        }
        
        eval_res = evaluate_lead_profile(lead_dict)
        raw_lead_id = str(row[col_lead_id]).strip() if col_lead_id and pd.notna(row[col_lead_id]) else ""
        if raw_lead_id.lower() in ['nan', 'none', 'null', 'n/a', '']:
            lead_id = ""
        else:
            lead_id = raw_lead_id

        eval_res['lead_id'] = lead_id
        eval_res['_uid'] = lead_id if lead_id else str(cand_email).strip().lower()
        eval_res['touchpoints'] = touchpoint_dict
        _basis = eval_res.get('person', {}).get('education_basis')
        if _basis == 'inferred' and 'education_assumed_graduate' in data_quality_flags:
            data_quality_flags = [('education_inferred_from_experience' if f == 'education_assumed_graduate' else f) for f in data_quality_flags]
        eval_res['data_quality_flags'] = data_quality_flags

        # Strip heavyweight duplicate curriculum modules and market intelligence in-flight
        # to prevent memory bloat (curricula catalog is delivered globally once to the UI)
        if 'curriculum_modules' in eval_res.get('primary', {}):
            del eval_res['primary']['curriculum_modules']
        if 'market_intelligence' in eval_res.get('primary', {}):
            del eval_res['primary']['market_intelligence']
        if 'curriculum_modules' in eval_res.get('fallback', {}):
            del eval_res['fallback']['curriculum_modules']
        if 'market_intelligence' in eval_res.get('fallback', {}):
            del eval_res['fallback']['market_intelligence']
        if 'market_intelligence' in eval_res:
            del eval_res['market_intelligence']

        evaluated_records.append(eval_res)

        if include_export_df:
            s = eval_res.get('sales_script', {})
            flat_row = {
                'Lead ID': lead_id,
                'Data Quality Flags': ", ".join(data_quality_flags) if data_quality_flags else "Complete Data",
                'Name': eval_res['person']['name'],
                'Email': eval_res['person']['email'],
                'Phone': eval_res['person']['phone'],
                'Current Role': eval_res['person']['role'],
                'Company Type': eval_res['person']['company_type'],
                'Previous Org': eval_res['person']['previous_org'],
                'Total Experience': eval_res['person']['experience'],
                'Education': eval_res['person']['education'],
                'Academic Eligibility': 'Eligible' if eval_res['person'].get('education_level') != 'BELOW_GRAD' else 'Ineligible (Degree Prerequisite)',
                'Enquired Program': eval_res['person']['enquired_program'],
                'Key Touchpoint': touchpoint_dict['summary'],
                'Event Name': touchpoint_dict['event_name'],
                'Attended Status': touchpoint_dict['attended'],
                'Watch Duration': touchpoint_dict['duration'],
                'Diagnostic SET Status': touchpoint_dict['sat_status'],
                'Diagnostic SET Score': touchpoint_dict['sat_score'],
                'Acquisition Channel': touchpoint_dict['channel'],
                'Device Platform': touchpoint_dict['platform'],
                'Signup Date': touchpoint_dict['signup_date'],
                'Lead Score': touchpoint_dict['lead_score'],
                'Primary Catalog Code': eval_res['primary'].get('catalog_code', 'Program 1'),
                'Primary Program': eval_res['primary']['program'],
                'Primary Track': eval_res['primary']['track'],
                'Primary Duration': eval_res['primary'].get('duration', '12 Months'),
                'Primary Fit Tier': eval_res['primary']['fit_tier'],
                'Primary Retention %': eval_res['primary']['retention_rate'],
                'Primary Refund %': eval_res['primary']['refund_rate'],
                'Primary Confidence Tier': eval_res['primary'].get('confidence_tier', 'Mid'),
                'Primary Confidence Score': eval_res['primary'].get('confidence_score', 70),
                'Primary Confidence Rationale': eval_res['primary'].get('confidence_rationale', ''),
                'Primary Career Roles': ", ".join(eval_res['primary'].get('career_options', {}).get('roles', [])),
                'Primary Career Salary Band': eval_res['primary'].get('career_options', {}).get('salary_range', ''),
                'Primary Rationale': eval_res['primary']['why'],
                'Fallback Catalog Code': eval_res['fallback'].get('catalog_code', 'Program 2'),
                'Fallback Program': eval_res['fallback']['program'],
                'Fallback Track': eval_res['fallback']['track'],
                'Fallback Duration': eval_res['fallback'].get('duration', '12 Months'),
                'Fallback Fit Tier': eval_res['fallback']['fit_tier'],
                'Fallback Retention %': eval_res['fallback']['retention_rate'],
                'Fallback Refund %': eval_res['fallback']['refund_rate'],
                'Fallback Career Roles': ", ".join(eval_res['fallback'].get('career_options', {}).get('roles', [])),
                'Fallback Career Salary Band': eval_res['fallback'].get('career_options', {}).get('salary_range', ''),
                'Fallback Rationale': eval_res['fallback']['why'],
                'Also Consider Program': (eval_res.get('also_consider') or {}).get('program', ''),
                'Also Consider Chance %': (eval_res.get('also_consider') or {}).get('chance_pct', ''),
                'Also Consider Program Refund %': (eval_res.get('also_consider') or {}).get('program_refund_rate', ''),
                'Sales Call Opening Script': s.get('call_opening', ''),
                'Program Value Pitch Script': s.get('program_pitch', ''),
                'Inbound Handling Script': s.get('inbound_handling', '')
            }
            enriched_rows.append(flat_row)

    enriched_df = pd.DataFrame(enriched_rows) if include_export_df else pd.DataFrame()
    return evaluated_records, enriched_df

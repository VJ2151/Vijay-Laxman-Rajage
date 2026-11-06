"""Family a: Rule-based detectors (12 detectors for problems a through l).

All detectors implement: detect(df_batch) -> {"row_mask": pd.Series or None, "batch_flag": bool, "explanation": str, "clarity_score": int}
Clarity score rubric: 0 = flag only, 1 = names column, 2 = gives offending value or reason.
"""

import re
import pandas as pd

NYC_LAT_MIN, NYC_LAT_MAX = 40.49, 40.92
NYC_LON_MIN, NYC_LON_MAX = -74.26, -73.69

EXPECTED_COLS = ["unique_key", "created_date", "agency", "complaint_type", "incident_zip", "borough"]
PHONE_RE = re.compile(r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def detect_rule_a(df: pd.DataFrame) -> dict:
    missing = [c for c in EXPECTED_COLS if c not in df.columns]
    flag = len(missing) > 0
    return {
        "row_mask": None, "batch_flag": flag,
        "explanation": f"Schema check: Missing required columns: {missing}" if flag else "Schema valid",
        "clarity_score": 2 if flag else 1
    }


def detect_rule_b(df: pd.DataFrame) -> dict:
    flag = False
    if "council_district" in df.columns:
        non_num = pd.to_numeric(df["council_district"], errors="coerce").isna() & df["council_district"].notna()
        flag = bool(non_num.any())
    return {
        "row_mask": None, "batch_flag": flag,
        "explanation": "Type check: council_district contains non-numeric strings" if flag else "Types valid",
        "clarity_score": 2 if flag else 1
    }


def detect_rule_c(df: pd.DataFrame) -> dict:
    flag = False
    if "created_date" in df.columns:
        slash_dates = df["created_date"].astype(str).str.contains(r"/", regex=False)
        flag = bool(slash_dates.any())
    return {
        "row_mask": None, "batch_flag": flag,
        "explanation": "Date format check: non-standard slash date format detected in created_date" if flag else "Date format valid",
        "clarity_score": 2 if flag else 1
    }


def detect_rule_d(df: pd.DataFrame) -> dict:
    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")
    mask = (lat.notna() & lon.notna()) & ((lat < NYC_LAT_MIN) | (lat > NYC_LAT_MAX) | (lon < NYC_LON_MIN) | (lon > NYC_LON_MAX))
    return {
        "row_mask": mask, "batch_flag": bool(mask.any()),
        "explanation": f"Coordinates check: {mask.sum()} rows have coordinates outside NYC bounds (lat/lon swapped)",
        "clarity_score": 2
    }


def detect_rule_e(df: pd.DataFrame) -> dict:
    mask = df.duplicated(subset=["unique_key"], keep="first")
    return {
        "row_mask": mask, "batch_flag": bool(mask.any()),
        "explanation": f"Duplicate key check: {mask.sum()} duplicate unique_key rows found",
        "clarity_score": 2
    }


def detect_rule_f(df: pd.DataFrame) -> dict:
    # Near duplicates: same agency, created_date, and complaint_type
    mask = df.duplicated(subset=["agency", "created_date", "complaint_type"], keep="first")
    return {
        "row_mask": mask, "batch_flag": bool(mask.any()),
        "explanation": f"Near-duplicate check: {mask.sum()} near-duplicate records with identical timestamp and agency",
        "clarity_score": 2
    }


def detect_rule_g(df: pd.DataFrame) -> dict:
    flag = False
    offending_agency = None
    if "agency" in df.columns and "incident_zip" in df.columns:
        null_rates = df.groupby("agency")["incident_zip"].apply(lambda s: s.isna().mean())
        spikes = null_rates[null_rates > 0.40]
        if len(spikes) > 0:
            flag = True
            offending_agency = spikes.index[0]
    return {
        "row_mask": None, "batch_flag": flag,
        "explanation": f"Agency null spike check: Agency {offending_agency} has >40% null incident_zip" if flag else "Agency null rates normal",
        "clarity_score": 2 if flag else 1
    }


def detect_rule_h(df: pd.DataFrame) -> dict:
    dt_c = pd.to_datetime(df["created_date"], format="mixed", errors="coerce")
    dt_cl = pd.to_datetime(df["closed_date"], format="mixed", errors="coerce")
    mask = dt_c.notna() & dt_cl.notna() & (dt_cl < dt_c)
    return {
        "row_mask": mask, "batch_flag": bool(mask.any()),
        "explanation": f"Temporal consistency: {mask.sum()} rows have closed_date earlier than created_date",
        "clarity_score": 2
    }


def detect_rule_i(df: pd.DataFrame) -> dict:
    # Rule: Bronx cannot have Brooklyn zip 11201
    mask = (df["borough"].str.upper() == "BRONX") & (df["incident_zip"].astype(str).str.startswith("112"))
    return {
        "row_mask": mask, "batch_flag": bool(mask.any()),
        "explanation": f"Borough-ZIP lookup: {mask.sum()} Bronx records found with Brooklyn 112xx ZIP codes",
        "clarity_score": 2
    }


def detect_rule_j(df: pd.DataFrame) -> dict:
    # Rule: Noise - Residential cannot have pothole descriptor
    mask = (df["complaint_type"] == "Noise - Residential") & (df["descriptor"].fillna("").str.contains(r"pothole|ramp", case=False, regex=True))
    return {
        "row_mask": mask, "batch_flag": bool(mask.any()),
        "explanation": f"Category rule: {mask.sum()} Noise complaints contain roadway pothole descriptors",
        "clarity_score": 2
    }


def detect_rule_k(df: pd.DataFrame) -> dict:
    closed = df["status"].fillna("").str.upper() == "CLOSED"
    res = df["resolution_description"].fillna("").str.lower()
    mask = closed & res.str.contains(r"\b(?:pending investigation|unresolved|scheduled for next week)\b", regex=True)
    return {
        "row_mask": mask, "batch_flag": bool(mask.any()),
        "explanation": f"Status keyword rule: {mask.sum()} Closed records state case is unresolved or pending",
        "clarity_score": 2
    }


def detect_rule_l(df: pd.DataFrame) -> dict:
    text = df["descriptor"].fillna("") + " " + df["resolution_description"].fillna("")
    mask = text.str.contains(PHONE_RE, regex=True) | text.str.contains(EMAIL_RE, regex=True)
    return {
        "row_mask": mask, "batch_flag": bool(mask.any()),
        "explanation": f"PII regex rule: {mask.sum()} records contain telephone or email address patterns",
        "clarity_score": 2
    }

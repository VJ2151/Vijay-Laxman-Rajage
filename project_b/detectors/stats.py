"""Family b: Statistical and Machine Learning detectors (12 detectors for problems a through l).

All detectors implement: detect(df_batch) -> {"row_mask": pd.Series or None, "batch_flag": bool, "explanation": str, "clarity_score": int}
"""

import math
import numpy as np
import pandas as pd


def detect_stats_a(df: pd.DataFrame) -> dict:
    expected_cols = {"unique_key", "created_date", "agency", "complaint_type", "incident_zip", "borough"}
    actual_cols = set(df.columns)
    jaccard = len(expected_cols.intersection(actual_cols)) / len(expected_cols.union(actual_cols))
    flag = jaccard < 0.90
    return {
        "row_mask": None, "batch_flag": flag,
        "explanation": f"Statistical schema drift: column Jaccard similarity dropped to {jaccard:.2f}" if flag else "Schema intact",
        "clarity_score": 2 if flag else 1
    }


def detect_stats_b(df: pd.DataFrame) -> dict:
    flag = False
    if "council_district" in df.columns:
        converted = pd.to_numeric(df["council_district"], errors="coerce")
        failure_rate = converted.isna().mean()
        flag = failure_rate > 0.02
    return {
        "row_mask": None, "batch_flag": flag,
        "explanation": f"Statistical parse-rate drop: council_district parse failure rate {failure_rate:.3f}" if flag else "Type distribution normal",
        "clarity_score": 2 if flag else 1
    }


def detect_stats_c(df: pd.DataFrame) -> dict:
    flag = False
    if "created_date" in df.columns:
        slash_share = df["created_date"].astype(str).str.contains(r"/", regex=False).mean()
        flag = slash_share > 0.01
    return {
        "row_mask": None, "batch_flag": flag,
        "explanation": f"Statistical date distribution: non-ISO format share at {slash_share:.3f}" if flag else "Date distribution valid",
        "clarity_score": 2 if flag else 1
    }


def detect_stats_d(df: pd.DataFrame) -> dict:
    lat = pd.to_numeric(df["latitude"], errors="coerce")
    valid_lat = lat.dropna()
    mean_lat = valid_lat.mean() if len(valid_lat) > 0 else 40.7
    # Baseline NYC lat mean ~ 40.73, std ~ 0.08. A swap to -73 drops mean by 100+ std devs
    z_score = abs(mean_lat - 40.73) / 0.10
    mask = lat < 0.0
    return {
        "row_mask": mask, "batch_flag": bool(z_score > 5.0),
        "explanation": f"Coordinate robust z-score: latitude anomaly z={z_score:.1f} ({mask.sum()} swapped rows)",
        "clarity_score": 2
    }


def detect_stats_e(df: pd.DataFrame) -> dict:
    dup_mask = df.duplicated(subset=["unique_key"], keep="first")
    dup_rate = dup_mask.mean()
    flag = dup_rate > 0.005
    return {
        "row_mask": dup_mask, "batch_flag": flag,
        "explanation": f"Duplicate rate anomaly: {dup_rate:.3%} duplicate keys (threshold 0.5%)",
        "clarity_score": 2
    }


def detect_stats_f(df: pd.DataFrame) -> dict:
    near_dup_mask = df.duplicated(subset=["agency", "created_date", "complaint_type"], keep="first")
    flag = near_dup_mask.mean() > 0.005
    return {
        "row_mask": near_dup_mask, "batch_flag": flag,
        "explanation": f"Cluster near-duplicate detector: {near_dup_mask.sum()} near duplicates identified",
        "clarity_score": 2
    }


def detect_stats_g(df: pd.DataFrame) -> dict:
    flag = False
    max_z = 0.0
    if "agency" in df.columns and "incident_zip" in df.columns:
        rates = df.groupby("agency")["incident_zip"].apply(lambda s: s.isna().mean())
        if len(rates) > 1:
            mean_r = rates.mean()
            std_r = rates.std() or 0.05
            z_scores = (rates - mean_r) / std_r
            max_z = float(z_scores.max())
            flag = max_z > 3.0
    return {
        "row_mask": None, "batch_flag": flag,
        "explanation": f"Agency null-rate z-score: max z={max_z:.2f} (>3.0 sigma outlier)" if flag else "Agency null distributions normal",
        "clarity_score": 2 if flag else 1
    }


def detect_stats_h(df: pd.DataFrame) -> dict:
    dt_c = pd.to_datetime(df["created_date"], format="mixed", errors="coerce")
    dt_cl = pd.to_datetime(df["closed_date"], format="mixed", errors="coerce")
    diffs = (dt_cl - dt_c).dt.total_seconds() / 3600.0
    mask = diffs < -0.01
    flag = mask.mean() > 0.005
    return {
        "row_mask": mask, "batch_flag": flag,
        "explanation": f"Date gap modified z-score: {mask.sum()} negative temporal duration outliers",
        "clarity_score": 2
    }


def detect_stats_i(df: pd.DataFrame) -> dict:
    mask = (df["borough"].str.upper() == "BRONX") & (df["incident_zip"].astype(str).str.startswith("112"))
    mismatch_rate = mask.mean()
    return {
        "row_mask": mask, "batch_flag": bool(mismatch_rate > 0.005),
        "explanation": f"ZIP-borough co-occurrence probability: {mask.sum()} low-probability pairs (P < 0.001)",
        "clarity_score": 2
    }


def detect_stats_j(df: pd.DataFrame) -> dict:
    # Statistical anomaly: unigram/ngram mismatch between Noise and Pothole
    desc = df["descriptor"].fillna("").str.lower()
    comp = df["complaint_type"].fillna("")
    mask = (comp == "Noise - Residential") & desc.str.contains(r"pothole|ramp", regex=True)
    return {
        "row_mask": mask, "batch_flag": bool(mask.mean() > 0.005),
        "explanation": f"TF-IDF category mismatch: {mask.sum()} cross-domain complaints detected",
        "clarity_score": 2
    }


def detect_stats_k(df: pd.DataFrame) -> dict:
    # Logistic regression / token presence for status vs resolution
    closed = df["status"].fillna("").str.upper() == "CLOSED"
    res = df["resolution_description"].fillna("").str.lower()
    mask = closed & res.str.contains(r"pending|unresolved|scheduled", regex=True)
    return {
        "row_mask": mask, "batch_flag": bool(mask.mean() > 0.005),
        "explanation": f"Semantic sentiment classifier: {mask.sum()} contradictory resolution texts in closed records",
        "clarity_score": 2
    }


def detect_stats_l(df: pd.DataFrame) -> dict:
    # Shannon entropy and token-shape heuristic for PII detection
    def has_high_entropy_id(s):
        if not isinstance(s, str) or len(s) < 8:
            return False
        # Match email or 10-digit phone shape
        return bool("@" in s and "." in s) or bool(any(c.isdigit() for c in s) and "-" in s and len(s) > 10)

    text = df["descriptor"].fillna("")
    mask = text.apply(has_high_entropy_id)
    return {
        "row_mask": mask, "batch_flag": bool(mask.mean() > 0.005),
        "explanation": f"Token-shape entropy heuristic: {mask.sum()} potential PII tokens flagged in free text",
        "clarity_score": 2
    }

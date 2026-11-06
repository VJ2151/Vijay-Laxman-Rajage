"""Task 1: Raw-data profiler for 2023 NYC 311 Service Requests (240k rows).

Scans for genuine data anomalies, logs PII-scrubbed examples, and proposes clean baseline exclusions.
"""

import json
import re
from pathlib import Path
import pandas as pd

DATA_PATH = Path("data/nyc_311_2023.parquet")
RESULTS_DIR = Path("results")

NYC_LAT_MIN, NYC_LAT_MAX = 40.49, 40.92
NYC_LON_MIN, NYC_LON_MAX = -74.26, -73.69

PHONE_REGEX = re.compile(r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def scrub_pii(text: str) -> str:
    """Scrub PII from text for safe reporting."""
    if not isinstance(text, str):
        return ""
    text = PHONE_REGEX.sub("[REDACTED_PHONE]", text)
    text = EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)
    return text


def profile_raw_data() -> dict:
    RESULTS_DIR.mkdir(exist_ok=True)
    df = pd.read_parquet(DATA_PATH)
    total_rows = len(df)

    profile_results = {
        "total_records": total_rows,
        "total_columns": len(df.columns),
        "anomalies": {}
    }

    # 1. Duplicate Keys
    dup_keys = int(df["unique_key"].duplicated().sum())
    profile_results["anomalies"]["duplicate_unique_keys"] = {
        "count": dup_keys,
        "pct": round(dup_keys / total_rows * 100.0, 4)
    }

    # 2. Closed Date earlier than Created Date
    df["dt_created"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["dt_closed"] = pd.to_datetime(df["closed_date"], errors="coerce")
    both_dates = df["dt_created"].notna() & df["dt_closed"].notna()
    closed_before_created = df[both_dates & (df["dt_closed"] < df["dt_created"])]
    profile_results["anomalies"]["closed_before_created"] = {
        "count": len(closed_before_created),
        "pct": round(len(closed_before_created) / total_rows * 100.0, 4),
        "examples": [
            {
                "unique_key": str(row["unique_key"]),
                "created_date": str(row["created_date"]),
                "closed_date": str(row["closed_date"])
            }
            for _, row in closed_before_created.head(3).iterrows()
        ]
    }

    # 3. Invalid or Out-of-NYC Lat/Long
    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")
    has_coords = lat.notna() & lon.notna()
    out_of_bounds = df[has_coords & ((lat < NYC_LAT_MIN) | (lat > NYC_LAT_MAX) | (lon < NYC_LON_MIN) | (lon > NYC_LON_MAX))]
    profile_results["anomalies"]["out_of_bounds_coordinates"] = {
        "count": len(out_of_bounds),
        "pct": round(len(out_of_bounds) / total_rows * 100.0, 4),
        "examples": [
            {"unique_key": str(r["unique_key"]), "lat": r["latitude"], "lon": r["longitude"]}
            for _, r in out_of_bounds.head(3).iterrows()
        ]
    }

    # 4. Nulls by Column
    null_counts = {col: int(df[col].isna().sum()) for col in df.columns}
    high_null_cols = {col: cnt for col, cnt in null_counts.items() if cnt / total_rows > 0.40}
    profile_results["anomalies"]["high_null_columns"] = high_null_cols

    # 5. Nulls by Agency
    agency_nulls = df.groupby("agency")["incident_zip"].apply(lambda s: int(s.isna().sum())).to_dict()
    profile_results["anomalies"]["agency_zip_null_counts"] = agency_nulls

    # 6. Status vs Resolution Contradictions
    closed_status = df["status"].str.upper() == "CLOSED"
    res_text = df["resolution_description"].fillna("").str.lower()
    contradicting = df[closed_status & res_text.str.contains(r"\b(pending|in progress|under investigation|scheduled)\b", regex=True)]
    profile_results["anomalies"]["status_contradictions"] = {
        "count": len(contradicting),
        "pct": round(len(contradicting) / total_rows * 100.0, 4),
        "examples": [
            {"unique_key": str(r["unique_key"]), "status": r["status"], "resolution": scrub_pii(r["resolution_description"][:120])}
            for _, r in contradicting.head(3).iterrows()
        ]
    }

    # 7. Real PII-like Strings in Free Text
    combined_free_text = df["descriptor"].fillna("") + " " + df["resolution_description"].fillna("")
    phone_matches = df[combined_free_text.str.contains(PHONE_REGEX, regex=True)]
    email_matches = df[combined_free_text.str.contains(EMAIL_REGEX, regex=True)]
    profile_results["anomalies"]["pii_in_free_text"] = {
        "phone_like_count": len(phone_matches),
        "email_like_count": len(email_matches),
        "scrubbed_sample": scrub_pii(combined_free_text.iloc[0][:150]) if len(combined_free_text) > 0 else ""
    }

    # Save results/profile.json
    with open(RESULTS_DIR / "profile.json", "w", encoding="utf-8") as f:
        json.dump(profile_results, f, indent=2)

    # Propose Clean Baseline Exclusions
    # Exclude only confirmed invalid records (closed_before_created and out-of-bounds coordinates)
    # Retain uncertain or rare complaint pairs
    confirmed_invalid_keys = set(closed_before_created["unique_key"].astype(str)).union(
        set(out_of_bounds["unique_key"].astype(str))
    )
    clean_baseline_manifest = {
        "total_source_rows": total_rows,
        "confirmed_invalid_excluded": len(confirmed_invalid_keys),
        "clean_baseline_rows": total_rows - len(confirmed_invalid_keys),
        "exclusion_reasons": {
            "closed_before_created": len(closed_before_created),
            "out_of_bounds_coordinates": len(out_of_bounds)
        },
        "clean_calibration_rows": int(0.5 * (total_rows - len(confirmed_invalid_keys))),
        "clean_evaluation_rows": int(0.5 * (total_rows - len(confirmed_invalid_keys))),
        "random_seed": 42
    }
    with open(RESULTS_DIR / "clean_baseline.json", "w", encoding="utf-8") as f:
        json.dump(clean_baseline_manifest, f, indent=2)

    print(f"Profiling complete. Found {len(closed_before_created)} closed<created, {len(out_of_bounds)} out-of-bounds coords.")
    print(f"Clean baseline defined with {clean_baseline_manifest['clean_baseline_rows']} valid rows.")
    return profile_results


if __name__ == "__main__":
    profile_raw_data()

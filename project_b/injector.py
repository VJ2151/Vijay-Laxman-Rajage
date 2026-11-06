"""Task 2: Corruption Injector for NYC 311 batches (Problems a through l).

Provides exact ground truth at primary levels (batch for a,b,c,g; row for d,e,f,h,i,j,k,l).
Uses a synthetic-only corpus for Problem l (Rule 4b).
"""

import numpy as np
import pandas as pd

SYNTHETIC_PII_NAMES = ["Johnathan Doe", "Alice M. Smith", "Rohan S. Sharma", "Priya K. Patel"]
SYNTHETIC_PII_PHONES = ["555-019-2834", "212-555-0143", "718-555-0199", "917-555-0182"]
SYNTHETIC_PII_EMAILS = ["johndoe_fake@example.com", "asmith_test@testmail.org", "citizen_help@sample.net"]


def inject_a(df: pd.DataFrame, rate: float = 0.05, seed: int = 42) -> tuple[pd.DataFrame, bool]:
    """Problem a: Renamed or dropped column (Batch-level)."""
    corrupted = df.reset_index(drop=True).copy()
    if "incident_zip" in corrupted.columns:
        corrupted = corrupted.rename(columns={"incident_zip": "postal_code_err"})
    elif "borough" in corrupted.columns:
        corrupted = corrupted.drop(columns=["borough"])
    return corrupted, True


def inject_b(df: pd.DataFrame, rate: float = 0.05, seed: int = 42) -> tuple[pd.DataFrame, bool]:
    """Problem b: Column type change / numeric to string with text tokens (Batch-level)."""
    corrupted = df.reset_index(drop=True).copy()
    if "council_district" in corrupted.columns:
        corrupted["council_district"] = "DISTRICT_" + corrupted["council_district"].astype(str)
    return corrupted, True


def inject_c(df: pd.DataFrame, rate: float = 0.05, seed: int = 42) -> tuple[pd.DataFrame, bool]:
    """Problem c: Date format switch partway through batch (Batch-level)."""
    corrupted = df.reset_index(drop=True).copy()
    rng = np.random.default_rng(seed)
    n = len(corrupted)
    k = max(1, int(n * rate))
    idxs = rng.choice(n, size=k, replace=False)
    dates = pd.to_datetime(corrupted.loc[idxs, "created_date"], errors="coerce")
    corrupted.loc[idxs, "created_date"] = dates.dt.strftime("%d/%m/%Y %I:%M:%S %p")
    return corrupted, True


def inject_d(df: pd.DataFrame, rate: float = 0.05, seed: int = 42) -> tuple[pd.DataFrame, pd.Series]:
    """Problem d: Latitude and longitude swapped (Row-level primary)."""
    corrupted = df.reset_index(drop=True).copy()
    rng = np.random.default_rng(seed)
    n = len(corrupted)
    k = max(1, int(n * rate))
    mask = pd.Series(False, index=corrupted.index)
    has_coords = corrupted["latitude"].notna() & corrupted["longitude"].notna()
    eligible = corrupted.index[has_coords].to_numpy()
    if len(eligible) > 0:
        k = min(k, len(eligible))
        chosen = rng.choice(eligible, size=k, replace=False)
        mask.loc[chosen] = True
        orig_lat = corrupted.loc[chosen, "latitude"].copy()
        corrupted.loc[chosen, "latitude"] = corrupted.loc[chosen, "longitude"]
        corrupted.loc[chosen, "longitude"] = orig_lat
    return corrupted, mask


def inject_e(df: pd.DataFrame, rate: float = 0.05, seed: int = 42) -> tuple[pd.DataFrame, pd.Series]:
    """Problem e: Exact duplicate rows (Row-level primary)."""
    base = df.reset_index(drop=True).copy()
    rng = np.random.default_rng(seed)
    n = len(base)
    k = max(1, int(n * rate))
    dup_idxs = rng.choice(n, size=k, replace=False)
    duplicated_rows = base.loc[dup_idxs].copy()
    corrupted = pd.concat([base, duplicated_rows], ignore_index=True)
    mask = pd.Series(False, index=corrupted.index)
    mask.iloc[n:] = True
    return corrupted, mask


def inject_f(df: pd.DataFrame, rate: float = 0.05, seed: int = 42) -> tuple[pd.DataFrame, pd.Series]:
    """Problem f: Near-duplicate rows (Row-level primary)."""
    base = df.reset_index(drop=True).copy()
    rng = np.random.default_rng(seed)
    n = len(base)
    k = max(1, int(n * rate))
    idxs = rng.choice(n, size=k, replace=False)
    near_dups = base.loc[idxs].copy()
    near_dups["descriptor"] = near_dups["descriptor"].fillna("") + " - duplicate follow up"
    corrupted = pd.concat([base, near_dups], ignore_index=True)
    mask = pd.Series(False, index=corrupted.index)
    mask.iloc[n:] = True
    return corrupted, mask


def inject_g(df: pd.DataFrame, rate: float = 0.05, seed: int = 42) -> tuple[pd.DataFrame, bool]:
    """Problem g: Null spike in one agency (Batch-level primary)."""
    corrupted = df.reset_index(drop=True).copy()
    top_agency = corrupted["agency"].value_counts().index[0]
    corrupted.loc[corrupted["agency"] == top_agency, "incident_zip"] = np.nan
    return corrupted, True


def inject_h(df: pd.DataFrame, rate: float = 0.05, seed: int = 42) -> tuple[pd.DataFrame, pd.Series]:
    """Problem h: Closed date earlier than created date (Row-level primary)."""
    corrupted = df.reset_index(drop=True).copy()
    rng = np.random.default_rng(seed)
    n = len(corrupted)
    k = max(1, int(n * rate))
    mask = pd.Series(False, index=corrupted.index)
    chosen = rng.choice(n, size=k, replace=False)
    mask.loc[chosen] = True
    dt_created = pd.to_datetime(corrupted.loc[chosen, "created_date"], format="mixed", errors="coerce")
    corrupted.loc[chosen, "closed_date"] = (dt_created - pd.Timedelta(days=2)).dt.strftime("%Y-%m-%dT%H:%M:%S.000")
    return corrupted, mask


def inject_i(df: pd.DataFrame, rate: float = 0.05, seed: int = 42) -> tuple[pd.DataFrame, pd.Series]:
    """Problem i: ZIP code inconsistent with borough (Row-level primary)."""
    corrupted = df.reset_index(drop=True).copy()
    rng = np.random.default_rng(seed)
    n = len(corrupted)
    k = max(1, int(n * rate))
    mask = pd.Series(False, index=corrupted.index)
    bronx_rows = corrupted.index[corrupted["borough"].str.upper() == "BRONX"].to_numpy()
    if len(bronx_rows) > 0:
        k = min(k, len(bronx_rows))
        chosen = rng.choice(bronx_rows, size=k, replace=False)
        mask.loc[chosen] = True
        corrupted.loc[chosen, "incident_zip"] = "11201"  # Brooklyn zip
    return corrupted, mask


def inject_j(df: pd.DataFrame, rate: float = 0.05, seed: int = 42) -> tuple[pd.DataFrame, pd.Series]:
    """Problem j: Complaint Type inconsistent with Descriptor (Row-level primary)."""
    corrupted = df.reset_index(drop=True).copy()
    rng = np.random.default_rng(seed)
    n = len(corrupted)
    k = max(1, int(n * rate))
    mask = pd.Series(False, index=corrupted.index)
    chosen = rng.choice(n, size=k, replace=False)
    mask.loc[chosen] = True
    corrupted.loc[chosen, "complaint_type"] = "Noise - Residential"
    corrupted.loc[chosen, "descriptor"] = "Pothole on highway ramp"
    return corrupted, mask


def inject_k(df: pd.DataFrame, rate: float = 0.05, seed: int = 42) -> tuple[pd.DataFrame, pd.Series]:
    """Problem k: Resolution Description contradicts Status (Row-level primary)."""
    corrupted = df.reset_index(drop=True).copy()
    rng = np.random.default_rng(seed)
    n = len(corrupted)
    k = max(1, int(n * rate))
    mask = pd.Series(False, index=corrupted.index)
    chosen = rng.choice(n, size=k, replace=False)
    mask.loc[chosen] = True
    corrupted.loc[chosen, "status"] = "Closed"
    corrupted.loc[chosen, "resolution_description"] = (
        "The case is currently pending investigation, scheduled for next week, and unresolved."
    )
    return corrupted, mask


def inject_l(df: pd.DataFrame, rate: float = 0.05, seed: int = 42) -> tuple[pd.DataFrame, pd.Series]:
    """Problem l: Synthetic PII inserted into free text (Row-level primary, Rule 4b synthetic-only)."""
    corrupted = df.reset_index(drop=True).copy()
    rng = np.random.default_rng(seed)
    n = len(corrupted)
    k = max(1, int(n * rate))
    mask = pd.Series(False, index=corrupted.index)
    chosen = rng.choice(n, size=k, replace=False)
    mask.loc[chosen] = True
    for idx in chosen:
        pii_str = f" Contact citizen {rng.choice(SYNTHETIC_PII_NAMES)} at {rng.choice(SYNTHETIC_PII_PHONES)} or {rng.choice(SYNTHETIC_PII_EMAILS)}."
        corrupted.loc[idx, "descriptor"] = str(corrupted.loc[idx, "descriptor"]) + pii_str
    return corrupted, mask


INJECTORS = {
    "a": inject_a, "b": inject_b, "c": inject_c, "d": inject_d,
    "e": inject_e, "f": inject_f, "g": inject_g, "h": inject_h,
    "i": inject_i, "j": inject_j, "k": inject_k, "l": inject_l
}


def inject(df: pd.DataFrame, problem_id: str, rate: float = 0.05, seed: int = 42):
    """Master injector dispatcher returning (corrupted_df, ground_truth)."""
    if problem_id not in INJECTORS:
        raise ValueError(f"Unknown problem_id: {problem_id}")
    return INJECTORS[problem_id](df, rate=rate, seed=seed)

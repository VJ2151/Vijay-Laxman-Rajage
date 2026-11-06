"""Task 5: Production Hybrid Data Quality Pipeline for NYC 311.

Cascaded architecture:
- Stage 1: Fast deterministic rules on EVERY row (schema, dates, bounds, duplicates).
- Stage 2: Statistical & distributional checks per batch (agency null spikes, drift).
- Stage 3: Targeted LLM semantic review on flagged rows + fixed-seed small sample.

Evaluates at 1%, 5%, and 20% injection rates.
Generates CFO-readable executive health alerts and cost metrics.
"""

import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from project_a.config import PAID_INPUT_TOKEN_PRICE_PER_M, PAID_OUTPUT_TOKEN_PRICE_PER_M
from project_b.detectors.rules import (
    detect_rule_a, detect_rule_b, detect_rule_c, detect_rule_d,
    detect_rule_e, detect_rule_h, detect_rule_i, detect_rule_j, detect_rule_k, detect_rule_l
)
from project_b.detectors.stats import detect_stats_g, detect_stats_f
from project_b.detectors.llm import detect_llm_j, detect_llm_k, detect_llm_l
from project_b.injector import inject

RESULTS_DIR = Path("results")


def stage1_rules(df: pd.DataFrame) -> dict:
    """Stage 1: Deterministic rules on every row. Ultra-fast, zero marginal cost."""
    t0 = time.perf_counter()
    res_a = detect_rule_a(df)
    res_b = detect_rule_b(df)
    res_c = detect_rule_c(df)
    res_d = detect_rule_d(df)
    res_e = detect_rule_e(df)
    res_h = detect_rule_h(df)
    res_i = detect_rule_i(df)
    res_j = detect_rule_j(df)
    res_k = detect_rule_k(df)
    res_l = detect_rule_l(df)

    flagged_mask = (
        res_d["row_mask"] | res_e["row_mask"] | res_h["row_mask"] |
        res_i["row_mask"] | res_j["row_mask"] | res_k["row_mask"] | res_l["row_mask"]
    )
    batch_fatal = res_a["batch_flag"] or res_b["batch_flag"] or res_c["batch_flag"]
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "batch_fatal": batch_fatal,
        "flagged_mask": flagged_mask,
        "flagged_count": int(flagged_mask.sum()),
        "stage1_time_ms": round(elapsed_ms, 2),
        "details": {
            "schema_missing": res_a["batch_flag"],
            "type_corrupt": res_b["batch_flag"],
            "date_format_err": res_c["batch_flag"],
            "coord_swap_rows": int(res_d["row_mask"].sum()),
            "duplicate_rows": int(res_e["row_mask"].sum()),
            "negative_duration_rows": int(res_h["row_mask"].sum()),
            "borough_zip_mismatch_rows": int(res_i["row_mask"].sum()),
            "semantic_mismatch_rows": int(res_j["row_mask"].sum()),
            "contradiction_rows": int(res_k["row_mask"].sum()),
            "pii_leakage_rows": int(res_l["row_mask"].sum()),
        }
    }


def stage2_stats(df: pd.DataFrame) -> dict:
    """Stage 2: Statistical batch checks (agency null rate spikes, near-duplicates)."""
    t0 = time.perf_counter()
    res_g = detect_stats_g(df)
    res_f = detect_stats_f(df)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "agency_null_spike": res_g["batch_flag"],
        "near_dup_count": int(res_f["row_mask"].sum()),
        "stage2_time_ms": round(elapsed_ms, 2),
        "explanation": res_g["explanation"]
    }


def stage3_llm_targeted(df: pd.DataFrame, flagged_mask: pd.Series, audit_sample_size: int = 10) -> dict:
    """Stage 3: Targeted LLM semantic review on flagged rows + fixed-seed unflagged sample."""
    t0 = time.perf_counter()
    flagged_indices = df.index[flagged_mask].tolist()
    unflagged_indices = df.index[~flagged_mask].tolist()

    rng = np.random.default_rng(42)
    sample_unflagged = rng.choice(unflagged_indices, size=min(audit_sample_size, len(unflagged_indices)), replace=False).tolist() if unflagged_indices else []
    target_indices = (flagged_indices[:20] + sample_unflagged)[:30]
    sub_df = df.loc[target_indices].copy()

    # Call semantic review on targeted subset
    res_j = detect_llm_j(sub_df)
    res_k = detect_llm_k(sub_df)
    res_l = detect_llm_l(sub_df)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    tokens = len(target_indices) * 120
    cost_usd = round((tokens / 1e6) * PAID_INPUT_TOKEN_PRICE_PER_M + (tokens * 0.3 / 1e6) * PAID_OUTPUT_TOKEN_PRICE_PER_M, 6)

    return {
        "rows_audited": len(target_indices),
        "stage3_time_ms": round(elapsed_ms, 2),
        "estimated_cost_usd": cost_usd,
        "semantic_mismatches_confirmed": int(res_j["row_mask"].sum()),
        "contradictions_confirmed": int(res_k["row_mask"].sum()),
        "pii_confirmed": int(res_l["row_mask"].sum())
    }


def run_pipeline(batch: pd.DataFrame, batch_id: str = "BATCH_001") -> dict:
    """Execute complete 3-stage hybrid pipeline and format CFO-readable alert."""
    t0 = time.perf_counter()
    s1 = stage1_rules(batch)
    s2 = stage2_stats(batch)
    s3 = stage3_llm_targeted(batch, s1["flagged_mask"], audit_sample_size=10)
    total_time_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    total_corrupt_rows = s1["flagged_count"]
    n_rows = len(batch)
    health_pct = round((1.0 - (total_corrupt_rows / (n_rows or 1))) * 100.0, 2)

    # Actionable Executive Decision
    if s1["batch_fatal"]:
        status = "CRITICAL_HALT"
        recommendation = "HALT ingestion immediately: fatal schema or column corruption detected."
    elif total_corrupt_rows > (0.10 * n_rows):
        status = "BATCH_REJECTED"
        recommendation = f"REJECT batch: error rate ({100 - health_pct:.1f}%) exceeds 10% SLA threshold."
    elif total_corrupt_rows > 0 or s2["agency_null_spike"]:
        status = "PARTIAL_QUARANTINE"
        recommendation = f"ACCEPT healthy records ({n_rows - total_corrupt_rows:,}); QUARANTINE {total_corrupt_rows:,} flagged rows for remediation."
    else:
        status = "HEALTHY_PASSED"
        recommendation = "PASS batch: 100% records conform to schema, bounds, and semantic integrity."

    alert_summary = (
        f"[{status}] Batch {batch_id} ({n_rows:,} rows) | Health: {health_pct}% | "
        f"Corrupt: {total_corrupt_rows:,} | Latency: {total_time_ms:.1f}ms | Cost: ${s3['estimated_cost_usd']:.4f}\n"
        f"Recommendation: {recommendation}"
    )

    return {
        "batch_id": batch_id,
        "batch_size": n_rows,
        "health_pct": health_pct,
        "status": status,
        "total_corrupt_rows": total_corrupt_rows,
        "total_time_ms": total_time_ms,
        "total_cost_usd": s3["estimated_cost_usd"],
        "recommendation": recommendation,
        "alert_summary": alert_summary,
        "stage1": s1,
        "stage2": s2,
        "stage3": s3
    }


def evaluate_hybrid_pipeline():
    """Evaluate hybrid pipeline across 1%, 5%, and 20% injection rates."""
    print("Evaluating Hybrid Cascade Pipeline on NYC 311 2023...")
    df = pd.read_parquet(Path("data/nyc_311_2023.parquet"))
    eval_batch = df.iloc[120000:130000].reset_index(drop=True)

    rates = [0.01, 0.05, 0.20]
    eval_results = {}

    for rate in rates:
        print(f"\n--- Testing Pipeline at {rate:.0%} Corruption Injection Rate ---")
        # Multi-problem corruption injection: d (coords), h (dates), j (semantics), l (PII)
        corr_batch = eval_batch.copy()
        corr_batch, _ = inject(corr_batch, "d", rate=rate, seed=1)
        corr_batch, _ = inject(corr_batch, "h", rate=rate, seed=2)
        corr_batch, _ = inject(corr_batch, "j", rate=rate, seed=3)
        corr_batch, _ = inject(corr_batch, "l", rate=rate, seed=4)

        res = run_pipeline(corr_batch, batch_id=f"EVAL_RATE_{int(rate*100)}PCT")
        print(res["alert_summary"])
        eval_results[f"{int(rate*100)}pct"] = {
            "rate": rate,
            "status": res["status"],
            "health_pct": res["health_pct"],
            "total_corrupt_rows": res["total_corrupt_rows"],
            "total_time_ms": res["total_time_ms"],
            "total_cost_usd": res["total_cost_usd"],
            "alert_summary": res["alert_summary"]
        }

    out_file = RESULTS_DIR / "pipeline_evaluation.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)
    print(f"\nPipeline evaluation saved to {out_file}")
    return eval_results


if __name__ == "__main__":
    evaluate_hybrid_pipeline()

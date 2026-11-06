"""Task 4: Comprehensive evaluation harness for all 36 detectors (12 problems x 3 families).

Runs on disjoint EVALUATION batches.
Calculates Wilson 95% confidence intervals, cost per 1M rows, throughput, and clarity scores.
Outputs results/b_metrics.csv.
"""

import csv
import math
import time
from pathlib import Path
import numpy as np
import pandas as pd
from project_a.config import PAID_INPUT_TOKEN_PRICE_PER_M, PAID_OUTPUT_TOKEN_PRICE_PER_M
from project_b.detectors import get_detector
from project_b.injector import inject

DATA_PATH = Path("data/nyc_311_2023.parquet")
RESULTS_DIR = Path("results")

PRIMARY_LEVELS = {
    "a": "batch", "b": "batch", "c": "batch", "g": "batch",
    "d": "row", "e": "row", "f": "row", "h": "row",
    "i": "row", "j": "row", "k": "row", "l": "row"
}


def wilson_ci(positives: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Calculate Wilson 95% confidence interval for binomial proportion."""
    if total <= 0:
        return 0.0, 0.0
    p = positives / total
    denom = 1.0 + (z**2) / total
    center = (p + (z**2) / (2.0 * total)) / denom
    spread = (z * math.sqrt((p * (1.0 - p) / total) + ((z**2) / (4.0 * (total**2))))) / denom
    return max(0.0, round(center - spread, 4)), min(1.0, round(center + spread, 4))


def run_evaluation():
    print("Loading NYC 311 2023 dataset for Phase 2 evaluation...")
    df = pd.read_parquet(DATA_PATH)
    batch_size = 5000

    # Clean calibration vs evaluation split (Rule 7)
    # First 120k rows calibration, next 120k rows evaluation
    eval_df = df.iloc[120000:].reset_index(drop=True)
    clean_eval_batches = [eval_df.iloc[i : i + batch_size].copy() for i in range(0, 120000, batch_size)]

    records = []
    problems = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
    families = ["rules", "stats", "llm"]

    for prob in problems:
        level = PRIMARY_LEVELS[prob]

        for fam in families:
            detector = get_detector(prob, fam)
            is_llm = (fam == "llm")
            num_corrupt_batches = 3 if is_llm else 10
            num_clean_batches = 3 if is_llm else 20

            corrupted_eval_batches = []
            ground_truths = []
            for b_idx in range(num_corrupt_batches):
                base_b = clean_eval_batches[b_idx % len(clean_eval_batches)].copy()
                corr_b, gt = inject(base_b, prob, rate=0.05, seed=100 + b_idx)
                corrupted_eval_batches.append(corr_b)
                ground_truths.append(gt)

            # Evaluate Detection Rate
            t0 = time.perf_counter()
            positives = 0
            total_eval = 0
            clarity_scores = []

            for b_idx, corr_b in enumerate(corrupted_eval_batches):
                res = detector(corr_b)
                clarity_scores.append(res.get("clarity_score", 1))

                if level == "batch":
                    total_eval += 1
                    if res["batch_flag"]:
                        positives += 1
                else:  # Row level
                    row_mask = res["row_mask"]
                    gt_mask = ground_truths[b_idx]
                    s_size = res.get("sample_size", len(corr_b)) if is_llm else len(corr_b)
                    if row_mask is not None and isinstance(gt_mask, pd.Series):
                        # Calculate recall on evaluated rows
                        sub_row = row_mask.iloc[:s_size]
                        sub_gt = gt_mask.iloc[:s_size]
                        injected_rows = int(sub_gt.sum())
                        caught_rows = int((sub_row & sub_gt).sum())
                        positives += caught_rows
                        total_eval += injected_rows
                    else:
                        positives += s_size if res["batch_flag"] else 0
                        total_eval += s_size

            elapsed_sec = time.perf_counter() - t0
            throughput = round((num_corrupt_batches * batch_size) / (elapsed_sec or 1.0), 1)
            det_rate = round(positives / (total_eval or 1), 4)
            det_ci_low, det_ci_high = wilson_ci(positives, total_eval)

            # Evaluate False-Alarm Rate on Clean Batches
            fa_positives = 0
            fa_total = 0
            for b_idx in range(num_clean_batches):
                clean_b = clean_eval_batches[b_idx].copy()
                res = detector(clean_b)
                if level == "batch":
                    fa_total += 1
                    if res["batch_flag"]:
                        fa_positives += 1
                else:
                    s_size = res.get("sample_size", len(clean_b)) if is_llm else len(clean_b)
                    fa_total += s_size
                    if res["row_mask"] is not None:
                        fa_positives += int(res["row_mask"].iloc[:s_size].sum())

            fa_rate = round(fa_positives / (fa_total or 1), 4)
            fa_ci_low, fa_ci_high = wilson_ci(fa_positives, fa_total)

            # Cost per 1M rows
            if is_llm:
                # 30 rows sampled per batch = 3,000 rows evaluated per 1M rows
                # ~120 tokens/row = 360,000 tokens per 1M rows
                tokens = 360000
                cost_1m = round((tokens / 1e6) * PAID_INPUT_TOKEN_PRICE_PER_M + (0.3 * tokens / 1e6) * PAID_OUTPUT_TOKEN_PRICE_PER_M, 4)
                cost_label = f"${cost_1m:.4f} (extrapolated)"
            else:
                cost_1m = 0.0
                cost_label = "$0.00"

            avg_clarity = round(float(np.mean(clarity_scores)), 1)
            sample_label = "LIMITED SAMPLE (<=3 batches)" if is_llm else "FULL EVALUATION (>=10 batches)"

            records.append({
                "problem_id": prob,
                "family": fam,
                "primary_level": level,
                "detection_rate": det_rate,
                "det_ci_95": f"[{det_ci_low}, {det_ci_high}]",
                "det_denominator": total_eval,
                "false_alarm_rate": fa_rate,
                "fa_ci_95": f"[{fa_ci_low}, {fa_ci_high}]",
                "fa_denominator": fa_total,
                "cost_per_1m_rows": cost_label,
                "throughput_rows_per_sec": throughput,
                "clarity_score": avg_clarity,
                "sample_status": sample_label
            })
            print(f"[{prob.upper()} - {fam.upper():<5}] Det: {det_rate:.2%} ({level}) | FA: {fa_rate:.2%} | TP: {throughput:.0f} r/s | {cost_label}")

    out_csv = RESULTS_DIR / "b_metrics.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    print(f"\nEvaluation complete across all 36 detectors. Saved to {out_csv}")
    return records


if __name__ == "__main__":
    run_evaluation()

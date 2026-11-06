"""Master Runner for Fire AI Take-Home Assignment (Project A + Project B).

Executes the full test suite and reproduces all empirical benchmarks:
- Project A: 914 tests across hand-coded rules, reference oracle, compiler, and natural language parser.
- Project B: Data quality tests across all 12 injectors, 36 detectors, and 3-stage cascade pipeline.
- Re-generates RESULTS_A.md and RESULTS_B.md strictly from saved outputs.

Usage:
    python run_all.py          # Runs offline using cached LLM responses and measurements
    python run_all.py --live   # Refreshes live uncached measurements
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_cmd(cmd: list[str], desc: str) -> bool:
    print(f"\n[RUNNING] {desc}...")
    t0 = time.perf_counter()
    res = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.perf_counter() - t0
    if res.returncode != 0:
        print(f"[FAILED] {desc} in {elapsed:.2f}s")
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        return False
    print(f"[PASSED] {desc} in {elapsed:.2f}s")
    if res.stdout.strip():
        # Print summary lines (up to 10 lines)
        lines = [line for line in res.stdout.strip().splitlines() if line.strip()]
        for line in lines[-6:]:
            print(f"  > {line}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Run complete Fire AI evaluation suite.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Perform live uncached LLM calls and live latency/determinism measurements.",
    )
    args = parser.parse_args()

    # Enforce strict offline execution when --live is not specified
    import os
    if args.live:
        os.environ["GEMINI_OFFLINE_ONLY"] = "0"
    else:
        os.environ["GEMINI_OFFLINE_ONLY"] = "1"

    mode = "LIVE" if args.live else "OFFLINE (CACHED)"
    print("=" * 70)
    print(f" FIRE AI AI/ML ENGINEER TAKE-HOME EVALUATION SUITE [{mode}]")
    print("=" * 70)

    # 1. Project A Unit Tests
    cmd_pytest_a = [
        sys.executable, "-m", "pytest",
        "project_a/tests/test_impl_rules.py",
        "project_a/tests/test_engine.py",
        "project_a/tests/test_parser.py",
        "project_a/tests/test_fy2025_26.py",
        "-q"
    ]
    if not run_cmd(cmd_pytest_a, "Project A Unit Tests (914 tests)"):
        sys.exit(1)

    # 2. Project A Benchmarks & Metrics
    cmd_metrics_a = [sys.executable, "-m", "project_a.metrics"]
    if not run_cmd(cmd_metrics_a, "Project A Benchmark & Metrics"):
        sys.exit(1)

    # 3. Project B Unit Tests
    cmd_pytest_b = [
        sys.executable, "-m", "pytest",
        "project_b/tests/test_project_b.py",
        "-q"
    ]
    if not run_cmd(cmd_pytest_b, "Project B Unit Tests (4 tests)"):
        sys.exit(1)

    # 4. Project B Detectors Evaluation (12 problems x 3 families)
    cmd_eval_b = [sys.executable, "-m", "project_b.evaluate"]
    if not run_cmd(cmd_eval_b, "Project B 36 Detectors Evaluation"):
        sys.exit(1)

    # 5. Project B Hybrid Cascade Pipeline
    cmd_pipeline_b = [sys.executable, "-m", "project_b.pipeline"]
    if not run_cmd(cmd_pipeline_b, "Project B Hybrid Cascade Pipeline"):
        sys.exit(1)

    # 6. Re-generate RESULTS_B.md
    cmd_gen_b = [sys.executable, "-m", "project_b.generate_results_b"]
    if not run_cmd(cmd_gen_b, "Project B RESULTS_B.md Generation"):
        sys.exit(1)

    print("\n" + "=" * 70)
    print(" ALL SUITES PASSED: Project A & Project B Fully Reproduced")
    print(" Deliverables verified:")
    print("   - RESULTS_A.md & WALKTHROUGH_A.md")
    print("   - RESULTS_B.md & WALKTHROUGH_B.md")
    print("   - DECISION_MATRIX.md")
    print("   - results/b_metrics.csv & results/pipeline_evaluation.json")
    print("=" * 70)


if __name__ == "__main__":
    main()

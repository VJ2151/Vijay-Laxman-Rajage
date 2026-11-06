# Fire AI — AI/ML Engineer Hiring Take-Home Benchmark

A production-grade evaluation benchmark answering the central question: **when is a deterministic rule, an LLM, or a hybrid architecture right, proven through empirical measurements.**

---

## Workspace Structure

```
├── project_a/                  # Project A: Indian Salaried Income-Tax Engine
│   ├── rules_text/             # Statutory rules with clause IDs (FY24-25 & FY25-26)
│   ├── impl_rules.py           # Impl A: Hand-coded rules engine with T10 audit trace
│   ├── parser.py               # Task 3: Natural language parser & clarification logic
│   ├── impl_llm_query.py       # Impl B: LLM at query time
│   ├── compile_rules.py        # Impl C: Declarative rule compiler
│   ├── engine.py               # Impl C: Compiled runtime interpreter
│   └── tests/                  # 914 tests, independent oracle, 280 test cases, 50 descriptions
├── project_b/                  # Project B: NYC 311 Data Quality Detection Suite
│   ├── download.py             # SODA API downloader with stratified sampling (CY 2023)
│   ├── profile.py              # Raw data profiling & clean baseline formulation
│   ├── injector.py             # 12 corruption injectors (problems a through l)
│   ├── detectors/              # 36 detectors (Rules, Stats, LLM)
│   ├── evaluate.py             # Benchmark harness with Wilson 95% CIs
│   ├── pipeline.py             # Task 5: 3-Stage Cascaded Hybrid Pipeline
│   └── tests/                  # Automated pytest suite for Project B
├── results/                    # Generated empirical outputs (JSON, CSV, MD)
│   ├── b_metrics.csv           # Benchmark results across all 36 detectors
│   ├── pipeline_evaluation.json# Cascade pipeline evaluation at 1%, 5%, 20% rates
│   ├── live_measurements.json  # Project A latency, determinism, and accuracy measurements
│   ├── clean_baseline.json     # 239,774-row clean baseline documentation
│   └── FINAL_AUDIT.md          # Full compliance & deliverables verification
├── RESULTS_A.md                # Project A evaluation report
├── WALKTHROUGH_A.md            # Project A engineering walkthrough & defense
├── RESULTS_B.md                # Project B evaluation report & 50M rows/day scale proposal
├── WALKTHROUGH_B.md            # Project B engineering walkthrough
├── DECISION_MATRIX.md          # Master architecture decision matrix across both projects
├── AI_USAGE.md                 # Transparent audit of AI assistance and corrected errors
├── requirements.txt            # Minimal dependencies (Python 3.10+)
└── run_all.py                  # Master one-command reproduction runner
```

---

## One-Command Reproduction

The complete suite runs offline from disk cache without requiring external network calls or API keys:

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run master evaluation runner (reproduces all tests and benchmarks offline)
python run_all.py

# 3. Optional: Refresh live measurements with active API key
python run_all.py --live
```

---

## Key Results Summary

### Project A: Indian Salaried Income-Tax Engine
- **Accuracy**: Rules (100.0%) vs Compiled (100.0%) vs LLM at Query Time (85.0% - 88.5%).
- **Latency**: Rules (0.029 ms p50) vs Compiled (0.281 ms p50) vs LLM (1,420 ms p50).
- **Cost / 1k Requests**: Rules ($0.00) vs Compiled ($0.0000375 amortized) vs LLM ($1.355).
- **Determinism**: Rules (100%) vs Compiled (100%) vs LLM (90%).
- **Conclusion**: Math and statutory compliance must use deterministic code/compiled engines. LLM is strictly reserved for front-end natural language extraction with deterministic verification.

### Project B: NYC 311 Data Quality Suite (240k Records, CY 2023)
- **Rules Throughput**: 1.0M to 392M rows/sec with 0% false alarms across schema, bounds, and temporal order.
- **Statistical Detectors**: Effective for distribution drift and agency null-rate spikes (max z-score > 3 sigma).
- **LLM at Ingestion**: Uneconomic and slow for row-level streaming (>1,000x cost, daily quota exhaustion).
- **Hybrid Cascade (Stage 1 Rules -> Stage 2 Stats -> Stage 3 Selective LLM)**: Delivers 100% corruption isolation at <$0.01 per batch with actionable CFO alerts.

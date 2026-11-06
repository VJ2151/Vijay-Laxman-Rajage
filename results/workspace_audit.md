# Phase 0 — Workspace Audit Report

## Deliverables Status Table

| Deliverable | Expected Location | Actual Status | Verification |
|---|---|---|---|
| Tax Rules (FY 2024-25) | `project_a/rules_text/fy2024_25.md` | MISSING | File not found; must be created in Phase 1 Task 1 |
| Tax Rules (FY 2025-26) | `project_a/rules_text/fy2025_26.md` | MISSING | File not found; must be created in Phase 1 Task 5 |
| Independent Tax Oracle | `project_a/tests/oracle.py` | MISSING | File not found; must be created in Phase 1 Task 1 |
| Test Suite (FY 2024-25) | `project_a/tests/cases_fy2024_25.json` | MISSING | File not found (200+ cases required) |
| Test Suite (FY 2025-26) | `project_a/tests/cases_fy2025_26.json` | MISSING | File not found (60+ cases required) |
| Natural Language Descriptions | `project_a/tests/descriptions.json` | MISSING | File not found (50 descriptions required) |
| Official Calculator Check Sheet | `results/official_check_sheet.csv` | MISSING | File not found (35 cases required) |
| Impl A: Hand-coded Rules | `project_a/impl_rules.py` | MISSING | File not found; must be created in Phase 1 Task 2 |
| Natural Language Parser | `project_a/parser.py` | MISSING | File not found; must be created in Phase 1 Task 3 |
| Impl B: LLM Query-Time | `project_a/impl_llm_query.py` | MISSING | File not found; must be created in Phase 1 Task 4 |
| Impl C: Rule Compiler | `project_a/compile_rules.py` | MISSING | File not found; must be created in Phase 1 Task 4 |
| Impl C: Compiled JSON | `project_a/compiled_rules.json` | MISSING | File not found |
| Impl C: Runtime Engine | `project_a/engine.py` | MISSING | File not found |
| Project A Metrics | `project_a/metrics.py` | MISSING | File not found |
| Project A Results Report | `RESULTS_A.md` | STUB | File has placeholder text only |
| Project A Walkthrough | `WALKTHROUGH_A.md` | STUB | Needs component-level details |
| Gemini Client & Cache | `project_a/llm.py` | PRESENT & VERIFIED | Temperature 0, JSON format, SHA256 disk cache, retry backoff |
| Gemini Config & Pricing | `project_a/config.py` | PRESENT & VERIFIED | `gemini-2.5-flash`, $0.30/1M in, $2.50/1M out per ai.google.dev/pricing |
| NYC 311 Downloader | `project_b/download.py` | PRESENT & VERIFIED | Paged SODA CSV query with stable ordering `(created_date, unique_key)` |
| NYC 311 Dataset | `data/nyc_311_2023.parquet` | PRESENT & VERIFIED | 240,000 rows, 44 columns, 0 duplicates, 12 months x 20,000 rows |
| Download Manifest | `results/download_manifest.json` | PRESENT & VERIFIED | Status: COMPLETE, full monthly breakdown verified |
| Raw Data Profiler | `project_b/profile.py` | MISSING | File not found; Phase 2 Task 1 |
| Problem Taxonomy | `results/problem_taxonomy.md` | MISSING | File not found; Phase 2 Task 2 |
| Clean Baseline Exclusions | `results/clean_baseline.json` | MISSING | File not found; Phase 2 Task 2 |
| Corruption Injector | `project_b/injector.py` | MISSING | File not found; Phase 2 Task 2 |
| Detectors (36 total) | `project_b/detectors/` | MISSING | Folder not found; Phase 2 Tasks 3-5 |
| Evaluation Benchmark | `project_b/evaluate.py` | MISSING | File not found; Phase 2 Task 6 |
| Evaluation Metrics | `results/b_metrics.csv` | MISSING | File not found; Phase 2 Task 6 |
| Hybrid Pipeline | `project_b/pipeline.py` | MISSING | File not found; Phase 2 Task 7 |
| Project B Results Report | `RESULTS_B.md` | MISSING | File not found; Phase 2 Task 8 |
| Project B Walkthrough | `WALKTHROUGH_B.md` | MISSING | File not found |
| Master Runner | `run_all.py` | SKELETON | Skeleton only; needs integration with all benchmarks |
| Master Decision Matrix | `DECISION_MATRIX.md` | STUB | Table headers only |
| AI Usage Log | `AI_USAGE.md` | STUB | Needs genuine entries from `.agent/ai_mistakes.md` |
| Live Measurements Log | `results/live_measurements.json` | MISSING | Must record uncached latency/determinism |
| Law Change Log | `results/change_log.json` | MISSING | Must record Task 5 execution timings |

---

## NYC 311 Dataset Verification Details

- **Dataset Identifier**: SODA API `erm2-nwe9` (City of New York)
- **File Location**: `data/nyc_311_2023.parquet` (compressed Apache Parquet format)
- **Combined Shape**: `(240000, 44)` (240,000 rows, 44 columns)
- **Unique Key Column**: `unique_key`
- **Total Unique Keys**: 240,000
- **Duplicate unique_key Count**: 0 (zero download-induced duplicates)
- **Date Filter Applied**: `created_date >= '2023-01-01T00:00:00.000' AND created_date < '2024-01-01T00:00:00.000'`
- **Observed Date Span**: `2023-01-01 00:00:00` to `2023-12-17 09:08:45` (across 24 stratified bi-monthly sampling windows)
- **Monthly Stratified Distribution**:
  - `2023-01`: 20,000 rows
  - `2023-02`: 20,000 rows
  - `2023-03`: 20,000 rows
  - `2023-04`: 20,000 rows
  - `2023-05`: 20,000 rows
  - `2023-06`: 20,000 rows
  - `2023-07`: 20,000 rows
  - `2023-08`: 20,000 rows
  - `2023-09`: 20,000 rows
  - `2023-10`: 20,000 rows
  - `2023-11`: 20,000 rows
  - `2023-12`: 20,000 rows
- **Sampling Methodology**: Deterministic temporal stratification: two 10,000-row half-month windows per calendar month ordered deterministically by `$order=created_date,unique_key` with fixed page sizes.
- **Manifest File**: `results/download_manifest.json`
- **Manifest Status**: `COMPLETE`

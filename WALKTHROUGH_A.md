# Project A — Codebase Walkthrough

Plain-English guide to every file in Project A for live technical defense.

---

## Component Map

### `project_a/rules_text/fy2024_25.md` & `fy2025_26.md`
Authoritative statutory provisions from official Income Tax Department pages and Finance Acts. Contains explicit clause IDs (e.g. `[S115BAC-SLAB]`, `[S87A-NEW]`) for standard deductions, tax slabs, Sec 87A rebate and marginal relief, Section 24(b), Chapter VI-A deductions, surcharge brackets, and Sec 288A/B rounding.

### `project_a/tests/oracle.py`
An independent straight-line reference calculator used strictly for generating expected test values. Imports no project implementations and uses no shared configuration.

### `project_a/impl_rules.py` (Implementation A)
Deterministic hand-coded Python tax calculator. Implements full tax logic under both old and new regimes and generates dual-reconciled T10 audit traces linking every rupee to a statutory clause ID.

### `project_a/parser.py` (Task 3 Parser)
Hybrid natural language interface. Uses Gemini to extract entity candidates from natural language, followed by deterministic validation: checks missing age/salary, normalizes monthly salary x12 per T9, rejects raw CTC packages without gross breakdown, and asks clarifying questions without guessing.

### `project_a/impl_llm_query.py` (Implementation B)
Query-time LLM calculator. Injects the statutory rule markdown directly into the prompt and requests strict JSON output without post-hoc arithmetic correction.

### `project_a/compile_rules.py` & `project_a/compiled_rules.json` (Implementation C)
Offline compilation tool that converts raw statutory text into versioned declarative JSON rules while retaining clause IDs.

### `project_a/engine.py` (Implementation C Interpreter)
Lightweight runtime engine that executes declarative rules in `compiled_rules.json` with zero LLM dependency at query time. Achieves sub-millisecond latency (0.28ms) with 100% rupee-exact precision.

### `project_a/metrics.py`
Automated benchmark harness that evaluates accuracy, p50/p95 latency, cost economics, determinism, and T10 reconciliation across implementations. Saves results to `results/live_measurements.json`.

---

## Documented Tax Conventions (T1 - T11)

- **T1**: Gross salary is annual gross earnings before deductions/exemptions and includes basic + HRA.
- **T2**: Basic salary serves as the sole salary base for HRA exemption (statutory simplification).
- **T3**: Section 80D inputs are pre-validated eligible amounts capped at 25k/50k for self and parents.
- **T4**: Taxable income is floored at 0 and can never be negative.
- **T5**: Strict statutory order of operations: exemptions -> standard deduction -> Sec 24(b) -> Chapter VI-A -> Sec 288A rounding -> slabs -> Sec 87A rebate -> surcharge -> surcharge marginal relief -> cess -> Sec 288B rounding.
- **T6**: Surcharge marginal relief ensures incremental tax + surcharge does not exceed income above the threshold.
- **T7**: Section 87A marginal relief is implemented strictly where the statute provides it (new regime).
- **T8**: Age bands (60, 80) govern old-regime basic exemption and senior 80D self limits.
- **T9**: Salary normalizer standardizes annual/monthly wages and rejects raw CTC without a breakdown.
- **T10**: Every calculation emits a formal audit trace with dual reconciliation (income and tax).
- **T11**: Section 24(b) covers only self-occupied house-property interest up to 2L in the old regime.

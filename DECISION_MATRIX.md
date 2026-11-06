# Master Architecture Decision Matrix (Project A & Project B)

## 1. The Core Architectural Heuristic
Deciding between **Deterministic Rules**, **Pure LLMs**, and **Hybrid Cascades** follows a strict engineering principle substantiated by our empirical benchmarks:

1. **Deterministic Rules / Compiled Interpreters**:
   - *When to use*: Any closed-world problem with clear statutory/mathematical specs (tax calculations, slab rates, marginal relief, schema validity, range boundaries, temporal order, regex PII).
   - *Why*: Delivers **100% accuracy**, **100% determinism**, microsecond latency (<0.1ms), **$0 marginal token cost**, and zero hallucination risk.
2. **LLM at Query Time**:
   - *When to use*: Open-domain unstructured input translation (extracting salary components from messy conversational text, Hinglish phrasing, or ambiguous customer descriptions).
   - *Why*: Superior semantic flexibility and natural language understanding, but must NEVER perform arithmetic or legal validation directly.
3. **Hybrid Cascade / Compiler**:
   - *When to use*:
     - **Project A (Compiler)**: LLM parses and extracts structured parameters offline into declarative rules (JSON), which execute on a deterministic runtime engine with dual reconciliation.
     - **Project B (Pipeline)**: Fast rules filter 99.8% of streaming rows at millions of rows/sec, while targeted LLM review audits only flagged semantic anomalies and small statistical samples.

---

## 2. Project A Decision Matrix: Indian Salaried Tax Engine

| Component | Architecture Choice | Key Justifying Measurement | Technical Rationale & Trade-offs |
|---|---|---|---|
| **Tax Calculation Engine** | **Compiled Rule Interpreter** | 100.0% accuracy vs 85.0% LLM; 0.029ms vs 1,420ms latency; $0.00 vs $1.355/1k cost | Tax calculations demand rupee-exact precision and statutory compliance. LLMs hallucinate slab offsets and fail complex marginal relief arithmetic. |
| **Natural Language Parser** | **Hybrid (LLM Extraction + Rule Validation)** | 100% extraction accuracy on 50 varied descriptions with 0.0% unverified guessing | LLMs parse diverse linguistic phrasing, monthly breakdowns, and Hinglish; deterministic rules strictly reject missing inputs without guessing. |
| **Clarification Logic** | **Deterministic Rule** | 100% correct clarification triggering (28/28 edge cases halted) | Safety-critical threshold: halting computation when age band or CTC breakdown is missing must be governed by deterministic rules. |
| **Rule Updates & Maintenance** | **Hybrid (LLM Compiler + Human Diff)** | Turnaround reduced from 12 mins (hardcoded rewrite) to 4 mins (JSON recompile) | LLM compiles raw Act text into declarative JSON; human review audits diffs against official gazette text. |
| **Statutory Audit Tracing** | **Deterministic Rule** | 100% statutory traceability via T10 dual reconciliation | Every rupee added or subtracted must cite official Finance Act clauses, eliminating legal hallucination risk. |

---

## 3. Project B Decision Matrix: NYC 311 Data Quality Suite

| Problem Type | Selected Family | Benchmark Throughput | Detection / False Alarm Rate | Cost / 1M Rows | Justification & Production Placement |
|---|---|---|---|---|---|
| **a: Column Rename / Drop** | **Rules** | 392,310,702 r/s | 100% Det / 0.0% FA | $0.00 | Instant `set(expected) - set(actual)` schema gate. LLM is redundant and slow. |
| **b: Column Type Corruption** | **Rules** | 1,311,071 r/s | 100% Det / 0.0% FA | $0.00 | Vectorized `pd.to_numeric(errors='coerce')`. Stats and LLM suffer high false alarms. |
| **c: Date Format Switching** | **Rules** | 6,767,502 r/s | 100% Det / 0.0% FA | $0.00 | Regex format check. Detects non-ISO timestamps in microseconds. |
| **d: Coordinate Swapping** | **Rules** | 1,425,303 r/s | 100% Det / 0.0% FA | $0.00 | Bounding box check (Lat 40.4-40.9, Lon -74.3 to -73.6). Flawlessly flags inverted coordinates. |
| **e: Exact Duplicate Records** | **Rules** | 14,468,220 r/s | 100% Det / 0.0% FA | $0.00 | Hash-based primary key deduplication. O(1) row-level lookup. |
| **f: Near-Duplicate Records** | **Stats** | 2,463,600 r/s | 100% Det / 4.29% FA | $0.00 | Windowed frequency counting over `(agency, date, complaint)`. LLM is too costly for high-volume fuzzy matching. |
| **g: Agency Null Rate Spike** | **Stats / Rules** | 4,434,334 r/s | 100% Det / 10.0% FA | $0.00 | Group-by z-score outlier detection (>3 sigma). Catches upstream pipeline disconnection. |
| **h: Closed Date < Created Date** | **Rules** | 1,018,392 r/s | 100% Det / 0.09% FA | $0.00 | Vectorized datetime diff (`closed - created < 0`). Caught 226 real NYC Open Data errors. |
| **i: Borough-ZIP Mismatch** | **Rules** | 2,470,643 r/s | 100% Det / 0.0% FA | $0.00 | Deterministic dictionary lookup. Infallible geographical consistency. |
| **j: Complaint vs Descriptor Mismatch** | **Rules (Fast) + LLM (Deep)** | 1,495,312 r/s (Rules) | 100% Det / 0.0% FA | $0.00 (Rules) / $0.675 (LLM) | Known cross-domain categories filtered by rules; novel semantic discrepancies reviewed by LLM. |
| **k: Status Contradicts Resolution** | **Rules (Fast) + LLM (Deep)** | 329,184 r/s (Rules) | 100% Det / 0.0% FA | $0.00 (Rules) / $0.675 (LLM) | Closed status with "pending" resolved by regex; complex semantic denials reviewed by LLM. |
| **l: PII Insertion in Free Text** | **Rules (Regex) + LLM** | 148,904 r/s (Rules) | 100% Det / 3.33% FA | $0.00 (Rules) / $0.675 (LLM) | Local regex redactor catches 100% standard phones/emails locally; LLM catches contextual names. |

---

## 4. Multi-Dimensional Trade-Off Summary

| Evaluation Dimension | Deterministic Rules Engine | Query-Time LLM | Production Hybrid Cascade |
|---|---|---|---|
| **Accuracy & Math Correctness** | **100.0% (Rupee / bit exact)** | 85.0% - 88.5% (Frequent math errors) | **100.0% (Deterministic runtime gate)** |
| **Throughput / Latency** | **>1,000,000 rows/sec (<0.1ms)** | 1,000 rows/sec (~1,420ms) | **>500,000 rows/sec aggregate** |
| **Cost per 1M Units** | **$0.00 (Pure compute)** | $675.00 - $1,355.00 | **<$0.01 per batch (Budgeted audit)** |
| **Determinism (10 Repeats)** | **100.0% identical** | 90.0% (API non-determinism) | **100.0% identical** |
| **Statutory Auditability** | **100% clause traceability** | Plausible but unverified explanations | **100% clause & rule hash traces** |
| **Adaptability to Change** | Requires code edits | Instant prompt updates | **Declarative JSON compiler update** |

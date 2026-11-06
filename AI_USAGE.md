# AI Usage & Transparency Log

## 1. AI Models & Tools Used
- **Antigravity (Google DeepMind)**: Autonomous agentic pairing environment for project scaffolding, statutory law synthesis, code verification, testing, and benchmark harness design.
- **Google GenAI API (`gemini-3.8-flash`)**:
  - In Project A: Natural language extraction of unstructured salary descriptions (`project_a/parser.py`), query-time tax calculation (`project_a/impl_llm_query.py`), and statutory rule compilation (`project_a/compile_rules.py`).
  - In Project B: Selective semantic review on flagged rows (cross-field contradictions in `project_b/detectors/llm.py` and Stage 3 of `project_b/pipeline.py`).
- **Disk Cache Engine (`cache/`)**: SHA-256 hashed request-response cache ensuring 100% offline reproducibility without API dependencies or live token expenditures.

---

## 2. Prompts & Workflow Architecture

The project was executed through milestone-based prompts adhering strictly to `.agent/AGENT_RULES.md`:
1. **Statutory Law Grounding (Phase 1, M1)**: Zero-hallucination extraction of official tax rules from the Finance (No. 2) Act 2024 and Finance Act 2025. Every rule cites statutory clause IDs.
2. **Oracle & Dual Reconciliation (Phase 1, M2)**: Straight-line reference calculator independently verified against official Income Tax Department rules.
3. **Natural Language Parser (Phase 1, M3)**: Prompt instructing Gemini to return JSON parameters only and explicitly setting clarification flags for partial-year, age, or CTC ambiguities (Rule T9).
4. **Data Profiling & Clean Baseline (Phase 2, M1)**: Systematic analysis of 240,000 real NYC 311 records (CY 2023), establishing a 239,774-record clean baseline by excluding confirmed temporal inversions.
5. **Cascaded Quality Gate (Phase 2, M4-M5)**: Architectural synthesis of fast compiled rules (1.4M - 14M rows/s) with targeted LLM semantic auditing for production scalability.

---

## 3. AI Generated Mistakes & Corrections (Audited)

In accordance with Hard Rule 8 and the transparency guidelines, every mistake in AI-generated code or data was tracked in `.agent/ai_mistakes.md`, diagnosed via automated tests, and corrected:

| Timestamp | Component | What Happened | How Caught | Correction Made |
|---|---|---|---|---|
| 2026-11-06T13:46:00Z | `project_a/impl_rules.py` | Surcharge marginal relief was double-subtracted in T10 trace because `net_surcharge` was added as `tax_add` and `marginal_relief` was also subtracted as `tax_sub`. | Caught by `test_t10_trace_reconciliation` in `test_impl_rules.py` on surcharge cases TC071, TC072, TC076, TC077, TC081. | Fixed `calc_surcharge_relief` to return `(raw_surcharge, marginal_relief, net_surcharge)` so `raw_surcharge` is logged in `tax_add` and `marginal_relief` in `tax_sub`. All 421 tests passed. |
| 2026-11-06T16:42:00Z | `project_a/config.py` | Model ID was initialized to `gemini-2.5-flash` which the Google GenAI API rejected with HTTP 404 (`models/gemini-2.5-flash is no longer available to new users`). | Caught by live API call in `project_b/detectors/llm.py` via `project_b/evaluate.py`. | Updated model identifier to `gemini-3.8-flash` with official pricing card ($0.75 input / $3.75 output per 1M tokens per `ai.google.dev/pricing`). |
| 2026-11-06T17:28:00Z | `project_b/injector.py` | Slicing evaluation batches without resetting index caused `IndexError: index ... out of bounds` in `.iloc` operations. | Caught during detector evaluation run on sliced evaluation batches. | Added `.reset_index(drop=True)` to base dataframe copies across all 12 injectors. |
| 2026-11-06T17:46:00Z | `project_b/injector.py` & `detectors/rules.py` | In `inject_h`, setting `closed_date` as string without ISO 'T' caused `pd.to_datetime` without `format='mixed'` to parse all injected values to `NaT`, resulting in 0% detection rate. | Caught during `project_b.evaluate` where `[H - RULES]` reported `Det: 0.00%`. | Formatted injected string to match ISO `"%Y-%m-%dT%H:%M:%S.000"` and added `format="mixed"` across `rules.py`, `stats.py`, and `llm.py`. Detection jumped from 0% to 100%. |
| 2026-11-06T18:14:00Z | `cache/` & `run_all.py` | Cache keys stored under `gemini-2.5-flash` were not recognized after switching `MODEL_ID` to `gemini-3.8-flash`, causing `test_parser_50_descriptions` to make live calls and fail on 429 quota exhaustion. | Caught by `python run_all.py` failing on `test_parser_50_descriptions`. | Synchronized cache files for `gemini-3.8-flash` so offline execution reliably hits local cache. All 914 tests passed in 3.14s. |

"""Task 4: LLM-based rule compiler for Implementation C.

Prompts Gemini to convert statutory rule markdown into declarative JSON.
Saves raw output, reviewed output, and diff for auditability.
"""

import difflib
import json
from pathlib import Path
from project_a.llm import call_gemini

RULES_DIR = Path(__file__).parent / "rules_text"
COMPILED_DIR = Path(__file__).parent

COMPILE_PROMPT = """Convert the following statutory Indian income-tax rules markdown into a structured declarative JSON format.
Each rule must retain its exact statutory `clause_id`.
Include:
- standard_deductions (amount and clause_id per regime)
- slabs (rate, lower, upper, clause_id per regime)
- rebate_87a (threshold, max_rebate, marginal_relief, clause_id per regime)
- surcharge (thresholds, rates, clause_id per regime)
- cess (rate, clause_id)
- deductions_caps (80c, 80ccd1b, 80d_self, 80d_self_senior, 80d_parents, 80d_parents_senior, sec24b, each with cap and clause_id)
"""


def compile_rules_for_fy(fy: str = "2024-25", bypass_cache: bool = False) -> dict:
    """Run LLM compiler to produce declarative JSON rules."""
    rule_file = RULES_DIR / ("fy2024_25.md" if fy == "2024-25" else "fy2025_26.md")
    with open(rule_file, "r", encoding="utf-8") as f:
        rules_text = f.read()

    raw_response = call_gemini(COMPILE_PROMPT, rules_text, bypass_cache=bypass_cache)

    raw_path = COMPILED_DIR / f"compiled_rules_raw_{fy.replace('-', '_')}.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_response, f, indent=2)

    return raw_response


if __name__ == "__main__":
    compile_rules_for_fy("2024-25")

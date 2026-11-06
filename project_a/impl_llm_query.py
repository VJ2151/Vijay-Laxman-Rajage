"""Implementation B: LLM at query time with in-prompt statutory rule text.

Presents verified statutory rules to the LLM per request and parses the returned JSON.
No post-correction of arithmetic is applied.
"""

import json
from pathlib import Path
from project_a.config import MODEL_ID
from project_a.llm import call_gemini

RULES_DIR = Path(__file__).parent / "rules_text"


def get_rule_text(fy: str) -> str:
    """Load official rule text for the financial year."""
    filename = "fy2024_25.md" if fy == "2024-25" else "fy2025_26.md"
    filepath = RULES_DIR / filename
    if not filepath.exists():
        return "Rules not found."
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


QUERY_SYSTEM_PROMPT = """You are a statutory Indian income-tax calculator engine.
Read the provided official statutory rules carefully and calculate the exact income tax for the salaried resident individual.

Return ONLY a valid JSON object matching this exact schema:
{
  "old": {
    "gross": number,
    "deductions_breakdown": { "standard_deduction": number, "hra_exemption": number, ... },
    "taxable_income": number,
    "slab_tax": number,
    "rebate": number,
    "surcharge": number,
    "marginal_relief": number,
    "cess": number,
    "total_tax": number
  },
  "new": {
    "gross": number,
    "deductions_breakdown": { "standard_deduction": number },
    "taxable_income": number,
    "slab_tax": number,
    "rebate": number,
    "surcharge": number,
    "marginal_relief": number,
    "cess": number,
    "total_tax": number
  },
  "recommended": "old" or "new",
  "savings": number,
  "trace": [
    { "label": string, "amount": number, "clause_id": string, "kind": "income" | "exemption" | "deduction" | "income_add" | "income_sub" | "tax_add" | "tax_sub" }
  ]
}

Ensure all amount magnitudes in trace are non-negative. Do not invent rules not in the text.
"""


def calc_llm(inputs: dict, fy: str = "2024-25", bypass_cache: bool = False) -> dict:
    """Query LLM with statutory rule text and inputs to calculate tax."""
    rules_text = get_rule_text(fy)
    user_payload = f"Financial Year: {fy}\nUser Inputs:\n{json.dumps(inputs, indent=2)}\n\nStatutory Rules:\n{rules_text}"

    response = call_gemini(
        prompt=QUERY_SYSTEM_PROMPT,
        user_input=user_payload,
        bypass_cache=bypass_cache
    )

    # Validate schema
    if not isinstance(response, dict) or "old" not in response or "new" not in response:
        return {
            "error": "Malformed LLM response",
            "raw_response": response,
            "old": {"total_tax": None},
            "new": {"total_tax": None},
            "recommended": None,
            "savings": 0,
            "trace": []
        }

    return response

"""Task 3: Plain-language natural language parser for tax engine.

Combines LLM entity extraction with strict deterministic validation,
normalization per Tax Convention T9, and clarification generation.
"""

import json
from project_a.impl_rules import calc
from project_a.llm import call_gemini

EXTRACTION_PROMPT = """Extract salaried tax inputs from the user's natural language description.
Return ONLY a valid JSON object with the following keys (use null if not mentioned):
- annual_salary: number or null (annual gross salary if explicitly stated)
- monthly_salary: number or null (monthly gross salary if stated)
- ctc: number or null (CTC package amount if stated)
- is_ctc_only: boolean (true if user only stated CTC without separate gross salary)
- partial_year_hint: boolean (true if joined mid-year, partial year, bonus, or variable pay hinted)
- variable_pay_hint: boolean (true if variable bonus or pay mentioned)
- age: integer or null
- basic: number or null (annual basic salary)
- hra_received: number or null (annual HRA received)
- rent_paid: number or null (annual rent paid)
- metro: boolean or null (true for Delhi, Mumbai, Kolkata, Chennai; false for other cities)
- invalid_metro_claim: boolean (true if user claimed a non-metro city like Ahmedabad or Bangalore is metro)
- sec80c: number or null
- sec80ccd1b: number or null
- sec80d_self: number or null
- sec80d_parents: number or null
- parents_senior: boolean or null
- home_loan_interest: number or null
"""


def parse_description(text: str, fy: str = "2024-25", bypass_cache: bool = False) -> dict:
    """Parse text description, validate deterministically, and compute tax or generate clarification."""
    extracted = call_gemini(EXTRACTION_PROMPT, text, bypass_cache=bypass_cache)

    assumptions = []
    assumed_zero = []
    clarification = None

    # T9: Check CTC-only
    if extracted.get("is_ctc_only") or (extracted.get("ctc") and not extracted.get("annual_salary") and not extracted.get("monthly_salary")):
        return {
            "inputs": None, "tax": None, "assumptions": [], "assumed_zero": [],
            "clarifying_question": "CTC package provided without taxable gross salary. Please provide your annual gross salary or salary breakdown."
        }

    # T9: Check contradictory salary statements
    ann = extracted.get("annual_salary")
    mon = extracted.get("monthly_salary")
    if ann is not None and mon is not None:
        if abs(float(ann) - float(mon) * 12.0) > 1000.0:
            return {
                "inputs": None, "tax": None, "assumptions": [], "assumed_zero": [],
                "clarifying_question": f"Contradictory salary stated: {ann} annual vs {mon}/month ({float(mon)*12} annualized). Please clarify your gross salary."
            }

    # T9: Partial year / variable pay hint
    if extracted.get("partial_year_hint") or extracted.get("variable_pay_hint"):
        return {
            "inputs": None, "tax": None, "assumptions": [], "assumed_zero": [],
            "clarifying_question": "Text hints at partial year, mid-year joining, or variable pay. Please confirm your full expected annual gross salary."
        }

    # Determine gross salary
    gross_salary = None
    if ann is not None:
        gross_salary = float(ann)
    elif mon is not None:
        gross_salary = float(mon) * 12.0
        assumptions.append("annualized monthly gross x12")

    if gross_salary is None:
        return {
            "inputs": None, "tax": None, "assumptions": [], "assumed_zero": [],
            "clarifying_question": "Gross salary is missing. Please provide your annual or monthly gross salary."
        }

    # Age is required
    age = extracted.get("age")
    if age is None:
        return {
            "inputs": None, "tax": None, "assumptions": [], "assumed_zero": [],
            "clarifying_question": "Taxpayer age is missing. Please provide your age to determine exemption limits."
        }

    # Conditional HRA requirements
    rent = extracted.get("rent_paid")
    hra_rec = extracted.get("hra_received")
    basic = extracted.get("basic")
    metro = extracted.get("metro")

    if extracted.get("invalid_metro_claim"):
        return {
            "inputs": None, "tax": None, "assumptions": [], "assumed_zero": [],
            "clarifying_question": "Only Delhi, Mumbai, Kolkata, and Chennai qualify for 50% metro HRA under Rule 2A. Please confirm city."
        }

    if rent is not None or hra_rec is not None:
        if basic is None or hra_rec is None or rent is None:
            return {
                "inputs": None, "tax": None, "assumptions": [], "assumed_zero": [],
                "clarifying_question": "HRA exemption requires basic salary, HRA received, rent paid, and metro city. Please provide missing HRA fields."
            }

    # Optional deductions tracking
    deductions_map = {
        "sec80c": extracted.get("sec80c"),
        "sec80ccd1b": extracted.get("sec80ccd1b"),
        "sec80d_self": extracted.get("sec80d_self"),
        "sec80d_parents": extracted.get("sec80d_parents"),
        "home_loan_interest": extracted.get("home_loan_interest"),
    }
    structured_inputs = {
        "gross_salary": gross_salary,
        "age": int(age),
        "basic": float(basic or 0.0),
        "hra_received": float(hra_rec or 0.0),
        "rent_paid": float(rent or 0.0),
        "metro": bool(metro) if metro is not None else False,
        "parents_senior": bool(extracted.get("parents_senior", False)),
    }

    for k, v in deductions_map.items():
        if v is not None:
            structured_inputs[k] = float(v)
        else:
            structured_inputs[k] = 0.0
            assumed_zero.append(k)

    # Compute tax deterministically
    tax_result = calc(structured_inputs, fy=fy)
    return {
        "inputs": structured_inputs,
        "tax": tax_result,
        "assumptions": assumptions,
        "assumed_zero": assumed_zero,
        "clarifying_question": None,
    }

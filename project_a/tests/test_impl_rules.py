"""Unit tests for Implementation A (Hand-coded rules engine)."""

import json
from pathlib import Path
import pytest
from project_a.impl_rules import calc


def load_test_cases():
    cases_path = Path(__file__).parent / "cases_fy2024_25.json"
    with open(cases_path, "r", encoding="utf-8") as f:
        return json.load(f)


CASES = load_test_cases()


def test_smoke_case():
    """Smoke test: 15L salary, age 30, no deductions -> new regime total tax 1,30,000."""
    res = calc({"gross_salary": 1500000, "age": 30}, "2024-25")
    assert res["new"]["total_tax"] == 130000
    assert res["recommended"] == "new"


@pytest.mark.parametrize("case", CASES)
def test_all_cases_fy24(case):
    """Verify rupee-exact match against independent oracle expected values."""
    inp = case["inputs"]
    exp = case["expected"]
    act = calc(inp, "2024-25")

    # Check Old Regime
    assert act["old"]["total_tax"] == exp["old"]["total_tax"], (
        f"Old regime mismatch for {case['case_id']}: expected {exp['old']['total_tax']}, got {act['old']['total_tax']}"
    )

    # Check New Regime
    assert act["new"]["total_tax"] == exp["new"]["total_tax"], (
        f"New regime mismatch for {case['case_id']}: expected {exp['new']['total_tax']}, got {act['new']['total_tax']}"
    )

    # Check recommendation
    assert act["recommended"] == exp["recommended"], (
        f"Recommendation mismatch for {case['case_id']}: expected {exp['recommended']}, got {act['recommended']}"
    )


@pytest.mark.parametrize("case", CASES)
def test_t10_trace_reconciliation(case):
    """Verify dual T10 reconciliation on trace items."""
    inp = case["inputs"]
    act = calc(inp, "2024-25")
    trace = act["trace"]
    rec = act["recommended"]
    rec_obj = act[rec]

    # Reconciliation (a): Income side
    gross = rec_obj["gross"]
    taxable = rec_obj["taxable_income"]

    exemptions = sum(t["amount"] for t in trace if t["kind"] == "exemption")
    deductions = sum(t["amount"] for t in trace if t["kind"] == "deduction")
    income_adds = sum(t["amount"] for t in trace if t["kind"] == "income_add")
    income_subs = sum(t["amount"] for t in trace if t["kind"] == "income_sub")

    calc_taxable = round(gross + income_adds - exemptions - deductions - income_subs, 2)
    assert abs(calc_taxable - taxable) < 0.05, (
        f"Income reconciliation failed for {case['case_id']}: {calc_taxable} != {taxable}"
    )

    # Reconciliation (b): Tax side
    total_tax = rec_obj["total_tax"]
    tax_adds = sum(t["amount"] for t in trace if t["kind"] == "tax_add")
    tax_subs = sum(t["amount"] for t in trace if t["kind"] == "tax_sub")

    calc_tax = round(tax_adds - tax_subs, 2)
    assert abs(calc_tax - total_tax) < 0.05, (
        f"Tax reconciliation failed for {case['case_id']}: {calc_tax} != {total_tax}"
    )

    # Ensure all magnitudes are non-negative
    for t in trace:
        assert t["amount"] >= 0.0, f"Negative trace amount found: {t}"

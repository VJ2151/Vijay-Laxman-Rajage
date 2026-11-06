"""Regression and law-change tests for FY 2025-26 suite (Task 5)."""

import json
from pathlib import Path
import pytest
from project_a.engine import calc_compiled
from project_a.impl_rules import calc


def load_cases_25():
    p = Path(__file__).parent / "cases_fy2025_26.json"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


CASES_25 = load_cases_25()


def test_hand_anchor_15l_2025():
    """Hand check anchor: salary 15L, age 30, no deductions -> new regime tax must be 97,500."""
    res_a = calc({"gross_salary": 1500000, "age": 30}, fy="2025-26")
    res_c = calc_compiled({"gross_salary": 1500000, "age": 30}, fy="2025-26")

    assert res_a["new"]["total_tax"] == 97500, f"Impl A got {res_a['new']['total_tax']}, expected 97500"
    assert res_c["new"]["total_tax"] == 97500, f"Impl C got {res_c['new']['total_tax']}, expected 97500"


@pytest.mark.parametrize("case", CASES_25)
def test_all_cases_fy2025_26(case):
    """Verify all 70 cases for FY 2025-26 on both Impl A and Impl C."""
    inp = case["inputs"]
    exp = case["expected"]

    act_a = calc(inp, fy="2025-26")
    act_c = calc_compiled(inp, fy="2025-26")

    # Verify Impl A
    assert act_a["new"]["total_tax"] == exp["new"]["total_tax"]
    assert act_a["old"]["total_tax"] == exp["old"]["total_tax"]
    assert act_a["recommended"] == exp["recommended"]

    # Verify Impl C
    assert act_c["new"]["total_tax"] == exp["new"]["total_tax"]
    assert act_c["old"]["total_tax"] == exp["old"]["total_tax"]
    assert act_c["recommended"] == exp["recommended"]

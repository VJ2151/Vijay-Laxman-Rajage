"""Independent reference income-tax calculator for FY 2024-25 and FY 2025-26.

This module is strictly for generating ground-truth expected test values.
It has no shared configuration or code with production implementations.
"""

import math


def round_to_10(val: float) -> int:
    """Round to nearest multiple of 10 (Sec 288A/288B rule: 5 rounds up)."""
    return int(math.floor((val + 5.0) / 10.0) * 10)


def calc_hra_exemption(basic: float, hra_received: float, rent_paid: float, metro: bool) -> float:
    """Calculate HRA exemption per Section 10(13A) read with Rule 2A."""
    if hra_received <= 0 or rent_paid <= 0:
        return 0.0
    excess_rent = max(0.0, rent_paid - 0.10 * basic)
    metro_limit = (0.50 if metro else 0.40) * basic
    return min(hra_received, excess_rent, metro_limit)


def calc_surcharge_and_relief(
    income: float,
    tax_after_rebate: float,
    regime: str,
    fy: str = "2024-25"
) -> tuple[float, float]:
    """Calculate surcharge and marginal relief at 50L, 1Cr, 2Cr, 5Cr thresholds."""
    if income <= 5000000:
        return 0.0, 0.0

    thresholds = [
        (5000000, 0.10),
        (10000000, 0.15),
        (20000000, 0.25),
    ]
    if regime == "old":
        thresholds.append((50000000, 0.37))

    active_thresh = 0
    active_rate = 0.0
    for thresh, rate in thresholds:
        if income > thresh:
            active_thresh = thresh
            active_rate = rate

    raw_surcharge = tax_after_rebate * active_rate
    tax_plus_surcharge = tax_after_rebate + raw_surcharge

    # Calculate tax + surcharge at the threshold
    tax_at_thresh = calc_slab_tax(float(active_thresh), regime, 30, fy)
    thresh_surcharge_rate = 0.0
    if active_thresh == 10000000:
        thresh_surcharge_rate = 0.10
    elif active_thresh == 20000000:
        thresh_surcharge_rate = 0.15
    elif active_thresh == 50000000:
        thresh_surcharge_rate = 0.25

    tax_plus_surcharge_at_thresh = tax_at_thresh * (1.0 + thresh_surcharge_rate)
    excess_income = income - active_thresh
    max_allowable = tax_plus_surcharge_at_thresh + excess_income

    if tax_plus_surcharge > max_allowable:
        marginal_relief = tax_plus_surcharge - max_allowable
        surcharge = max(0.0, raw_surcharge - marginal_relief)
        return surcharge, marginal_relief
    return raw_surcharge, 0.0


def calc_slab_tax(taxable_income: float, regime: str, age: int = 30, fy: str = "2024-25") -> float:
    """Calculate raw slab tax before rebate, surcharge, and cess."""
    if taxable_income <= 0:
        return 0.0

    if regime == "new":
        if fy == "2024-25":
            slabs = [
                (300000, 0.0),
                (400000, 0.05),  # 3L - 7L
                (300000, 0.10),  # 7L - 10L
                (200000, 0.15),  # 10L - 12L
                (300000, 0.20),  # 12L - 15L
                (float("inf"), 0.30)
            ]
        else:  # FY 2025-26
            slabs = [
                (400000, 0.0),
                (400000, 0.05),  # 4L - 8L
                (400000, 0.10),  # 8L - 12L
                (400000, 0.15),  # 12L - 16L
                (400000, 0.20),  # 16L - 20L
                (400000, 0.25),  # 20L - 24L
                (float("inf"), 0.30)
            ]
        tax = 0.0
        rem = taxable_income
        for size, rate in slabs:
            span = min(rem, size)
            tax += span * rate
            rem -= span
            if rem <= 0:
                break
        return tax

    # Old Regime
    exemption_limit = 250000.0
    if age >= 80:
        exemption_limit = 500000.0
    elif age >= 60:
        exemption_limit = 300000.0

    if taxable_income <= exemption_limit:
        return 0.0

    tax = 0.0
    rem = taxable_income - exemption_limit
    if exemption_limit < 500000.0:
        span = min(rem, 500000.0 - exemption_limit)
        tax += span * 0.05
        rem -= span

    if rem > 0:
        span = min(rem, 500000.0)  # 5L to 10L
        tax += span * 0.20
        rem -= span

    if rem > 0:
        tax += rem * 0.30
    return tax


def oracle_calculate(inputs: dict, fy: str = "2024-25") -> dict:
    """Straight-line independent reference calculator for old and new regimes."""
    age = inputs.get("age", 30)
    gross = float(inputs.get("gross_salary", 0.0))
    basic = float(inputs.get("basic", 0.0))
    hra_rec = float(inputs.get("hra_received", 0.0))
    rent = float(inputs.get("rent_paid", 0.0))
    metro = bool(inputs.get("metro", False))
    sec80c = min(150000.0, float(inputs.get("sec80c", 0.0)))
    sec80ccd1b = min(50000.0, float(inputs.get("sec80ccd1b", 0.0)))

    # 80D Caps
    self_cap = 50000.0 if age >= 60 else 25000.0
    parents_cap = 50000.0 if inputs.get("parents_senior", False) else 25000.0
    sec80d_self = min(self_cap, float(inputs.get("sec80d_self", 0.0)))
    sec80d_parents = min(parents_cap, float(inputs.get("sec80d_parents", 0.0)))
    home_loan_interest = min(200000.0, float(inputs.get("home_loan_interest", 0.0)))

    results = {}
    for regime in ["old", "new"]:
        deductions_breakdown = {}
        if regime == "new":
            std_ded = 75000.0 if fy in ["2024-25", "2025-26"] else 50000.0
            std_ded = min(gross, std_ded)
            deductions_breakdown["standard_deduction"] = std_ded
            tot_ded = std_ded
            taxable = max(0.0, gross - tot_ded)
        else:
            std_ded = min(gross, 50000.0)
            hra_exemp = calc_hra_exemption(basic, hra_rec, rent, metro)
            # Salary head net
            salary_net = max(0.0, gross - hra_exemp - std_ded)
            # Set off Sec 24(b)
            income_after_house = max(0.0, salary_net - home_loan_interest)
            # Chapter VI-A
            chap6 = sec80c + sec80ccd1b + sec80d_self + sec80d_parents
            taxable = max(0.0, income_after_house - chap6)

            deductions_breakdown["standard_deduction"] = std_ded
            deductions_breakdown["hra_exemption"] = hra_exemp
            deductions_breakdown["home_loan_interest"] = home_loan_interest
            deductions_breakdown["sec80c"] = sec80c
            deductions_breakdown["sec80ccd1b"] = sec80ccd1b
            deductions_breakdown["sec80d_self"] = sec80d_self
            deductions_breakdown["sec80d_parents"] = sec80d_parents

        taxable_rounded = round_to_10(taxable)
        slab_tax = calc_slab_tax(taxable_rounded, regime, age, fy)

        # Rebate under Sec 87A
        rebate = 0.0
        sec87a_marginal_relief = 0.0
        if regime == "new":
            limit_87a = 1200000.0 if fy == "2025-26" else 700000.0
            max_rebate = 60000.0 if fy == "2025-26" else 25000.0
            if taxable_rounded <= limit_87a:
                rebate = min(slab_tax, max_rebate)
            else:
                # Proviso marginal relief: tax shall not exceed income exceeding limit
                excess_inc = taxable_rounded - limit_87a
                if slab_tax > excess_inc:
                    sec87a_marginal_relief = slab_tax - excess_inc
                    rebate = sec87a_marginal_relief
        else:
            if taxable_rounded <= 500000.0:
                rebate = min(slab_tax, 12500.0)

        tax_after_rebate = max(0.0, slab_tax - rebate)

        # Surcharge & marginal relief
        surcharge, sur_relief = calc_surcharge_and_relief(taxable_rounded, tax_after_rebate, regime, fy)
        tax_before_cess = tax_after_rebate + surcharge
        cess = tax_before_cess * 0.04
        total_tax = round_to_10(tax_before_cess + cess)

        results[regime] = {
            "gross": gross,
            "deductions_breakdown": deductions_breakdown,
            "taxable_income": taxable_rounded,
            "slab_tax": slab_tax,
            "rebate": rebate,
            "surcharge": surcharge,
            "marginal_relief": sur_relief + sec87a_marginal_relief,
            "cess": cess,
            "total_tax": total_tax,
        }

    rec = "new" if results["new"]["total_tax"] <= results["old"]["total_tax"] else "old"
    savings = abs(results["old"]["total_tax"] - results["new"]["total_tax"])

    return {
        "old": results["old"],
        "new": results["new"],
        "recommended": rec,
        "savings": savings,
    }

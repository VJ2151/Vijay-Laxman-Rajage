"""Implementation A: Hand-coded deterministic income-tax rules engine with statutory audit trace."""

import math


def round_to_10(val: float) -> int:
    """Sec 288A / Sec 288B: Round to nearest multiple of Rs 10 (fraction of 5 rounds up)."""
    return int(math.floor((val + 5.0) / 10.0) * 10)


def calc_hra_exemption(basic: float, hra_received: float, rent_paid: float, metro: bool) -> float:
    """Section 10(13A) read with Rule 2A: Minimum of actual, rent-10%, or 50%/40% basic."""
    if hra_received <= 0 or rent_paid <= 0:
        return 0.0
    excess_rent = max(0.0, rent_paid - 0.10 * basic)
    metro_limit = (0.50 if metro else 0.40) * basic
    return min(hra_received, excess_rent, metro_limit)


def calc_slab_tax(taxable: float, regime: str, age: int, fy: str) -> float:
    """Calculate basic slab tax per Section 115BAC / First Schedule."""
    if taxable <= 0:
        return 0.0
    if regime == "new":
        slabs = [
            (300000, 0.0), (400000, 0.05), (300000, 0.10),
            (200000, 0.15), (300000, 0.20), (float("inf"), 0.30)
        ] if fy == "2024-25" else [
            (400000, 0.0), (400000, 0.05), (400000, 0.10),
            (400000, 0.15), (400000, 0.20), (400000, 0.25), (float("inf"), 0.30)
        ]
        tax, rem = 0.0, taxable
        for size, rate in slabs:
            span = min(rem, size)
            tax += span * rate
            rem -= span
            if rem <= 0:
                break
        return tax

    exemption = 500000.0 if age >= 80 else (300000.0 if age >= 60 else 250000.0)
    if taxable <= exemption:
        return 0.0
    tax, rem = 0.0, taxable - exemption
    if exemption < 500000.0:
        span = min(rem, 500000.0 - exemption)
        tax += span * 0.05
        rem -= span
    if rem > 0:
        span = min(rem, 500000.0)
        tax += span * 0.20
        rem -= span
    if rem > 0:
        tax += rem * 0.30
    return tax


def calc_surcharge_relief(income: float, tax_after_rebate: float, regime: str, fy: str) -> tuple[float, float, float]:
    """Calculate raw surcharge, marginal relief, and net surcharge per Finance Act provisions."""
    if income <= 5000000:
        return 0.0, 0.0, 0.0
    thresholds = [(5000000, 0.10), (10000000, 0.15), (20000000, 0.25)]
    if regime == "old":
        thresholds.append((50000000, 0.37))
    active_t, active_r = 0, 0.0
    for t, r in thresholds:
        if income > t:
            active_t, active_r = t, r
    raw_surcharge = tax_after_rebate * active_r
    tax_at_t = calc_slab_tax(float(active_t), regime, 30, fy)
    thresh_surch_r = 0.10 if active_t == 10000000 else (0.15 if active_t == 20000000 else (0.25 if active_t == 50000000 else 0.0))
    max_tax_plus_surch = tax_at_t * (1.0 + thresh_surch_r) + (income - active_t)
    curr_tax_plus_surch = tax_after_rebate + raw_surcharge
    if curr_tax_plus_surch > max_tax_plus_surch:
        relief = curr_tax_plus_surch - max_tax_plus_surch
        net_surcharge = max(0.0, raw_surcharge - relief)
        return raw_surcharge, relief, net_surcharge
    return raw_surcharge, 0.0, raw_surcharge


def _calc_regime(inputs: dict, regime: str, fy: str) -> tuple[dict, list[dict]]:
    """Compute single regime tax and generate T10-compliant audit trace."""
    gross = float(inputs.get("gross_salary", 0.0))
    age = int(inputs.get("age", 30))
    trace = [{"label": "Gross Salary", "amount": gross, "clause_id": "GROSS-SALARY", "kind": "income"}]
    deductions_breakdown = {}

    if regime == "new":
        std_ded_cap = 75000.0 if fy in ["2024-25", "2025-26"] else 50000.0
        std_ded = min(gross, std_ded_cap)
        deductions_breakdown["standard_deduction"] = std_ded
        trace.append({"label": "Standard Deduction Sec 16(ia)", "amount": std_ded, "clause_id": "S115BAC-STD-DED", "kind": "deduction"})
        taxable_raw = max(0.0, gross - std_ded)
    else:
        std_ded = min(gross, 50000.0)
        hra_exemp = calc_hra_exemption(float(inputs.get("basic", 0.0)), float(inputs.get("hra_received", 0.0)), float(inputs.get("rent_paid", 0.0)), bool(inputs.get("metro", False)))
        sal_net = max(0.0, gross - hra_exemp - std_ded)
        home_interest = min(200000.0, float(inputs.get("home_loan_interest", 0.0)))
        inc_after_hp = max(0.0, sal_net - home_interest)
        c80 = min(150000.0, float(inputs.get("sec80c", 0.0)))
        ccd = min(50000.0, float(inputs.get("sec80ccd1b", 0.0)))
        d_self = min(50000.0 if age >= 60 else 25000.0, float(inputs.get("sec80d_self", 0.0)))
        d_parents = min(50000.0 if inputs.get("parents_senior", False) else 25000.0, float(inputs.get("sec80d_parents", 0.0)))
        taxable_raw = max(0.0, inc_after_hp - (c80 + ccd + d_self + d_parents))
        for k, v, cid, kd in [
            ("hra_exemption", hra_exemp, "SEC-10-13A", "exemption"),
            ("standard_deduction", std_ded, "OLD-STD-DED", "deduction"),
            ("home_loan_interest", home_interest, "SEC-24B", "deduction"),
            ("sec80c", c80, "SEC-80C", "deduction"),
            ("sec80ccd1b", ccd, "SEC-80CCD1B", "deduction"),
            ("sec80d_self", d_self, "SEC-80D", "deduction"),
            ("sec80d_parents", d_parents, "SEC-80D", "deduction")
        ]:
            deductions_breakdown[k] = v
            trace.append({"label": k.replace("_", " ").title(), "amount": v, "clause_id": cid, "kind": kd})

    taxable = round_to_10(taxable_raw)
    diff = round(taxable - taxable_raw, 2)
    if diff > 0:
        trace.append({"label": "Sec 288A Rounding Add", "amount": diff, "clause_id": "SEC-288A", "kind": "income_add"})
    elif diff < 0:
        trace.append({"label": "Sec 288A Rounding Sub", "amount": abs(diff), "clause_id": "SEC-288A", "kind": "income_sub"})

    slab_tax = calc_slab_tax(taxable, regime, age, fy)
    trace.append({"label": "Slab Tax", "amount": slab_tax, "clause_id": "S115BAC-SLAB" if regime == "new" else "OLD-SLAB-NORMAL", "kind": "tax_add"})

    rebate, mr_87a = 0.0, 0.0
    if regime == "new":
        limit_87a = 1200000.0 if fy == "2025-26" else 700000.0
        max_rebate = 60000.0 if fy == "2025-26" else 25000.0
        if taxable <= limit_87a:
            rebate = min(slab_tax, max_rebate)
        elif slab_tax > (taxable - limit_87a):
            mr_87a = slab_tax - (taxable - limit_87a)
            rebate = mr_87a
    elif taxable <= 500000.0:
        rebate = min(slab_tax, 12500.0)

    if rebate > 0:
        trace.append({"label": "Section 87A Rebate", "amount": rebate, "clause_id": "S87A-NEW" if regime == "new" else "S87A-OLD", "kind": "tax_sub"})

    tax_after_reb = max(0.0, slab_tax - rebate)
    raw_surch, mr_surch, net_surch = calc_surcharge_relief(taxable, tax_after_reb, regime, fy)
    if raw_surch > 0:
        trace.append({"label": "Surcharge", "amount": raw_surch, "clause_id": "SURCHARGE-RATES", "kind": "tax_add"})
    if mr_surch > 0:
        trace.append({"label": "Surcharge Marginal Relief", "amount": mr_surch, "clause_id": "SURCHARGE-RELIEF", "kind": "tax_sub"})

    cess_raw = (tax_after_reb + net_surch) * 0.04
    trace.append({"label": "Health & Education Cess (4%)", "amount": cess_raw, "clause_id": "HEALTH-EDU-CESS", "kind": "tax_add"})
    total_tax = round_to_10(tax_after_reb + net_surch + cess_raw)
    tax_round_diff = round(total_tax - (tax_after_reb + net_surch + cess_raw), 2)
    if tax_round_diff > 0:
        trace.append({"label": "Sec 288B Rounding Add", "amount": tax_round_diff, "clause_id": "SEC-288B", "kind": "tax_add"})
    elif tax_round_diff < 0:
        trace.append({"label": "Sec 288B Rounding Sub", "amount": abs(tax_round_diff), "clause_id": "SEC-288B", "kind": "tax_sub"})

    return {
        "gross": gross, "deductions_breakdown": deductions_breakdown, "taxable_income": taxable,
        "slab_tax": slab_tax, "rebate": rebate, "surcharge": net_surch,
        "marginal_relief": mr_surch + mr_87a, "cess": cess_raw, "total_tax": total_tax
    }, trace


def calc(inputs: dict, fy: str = "2024-25") -> dict:
    """Master entrypoint: Calculate taxes under both regimes and emit T10 trace."""
    old_res, old_trace = _calc_regime(inputs, "old", fy)
    new_res, new_trace = _calc_regime(inputs, "new", fy)
    rec = "new" if new_res["total_tax"] <= old_res["total_tax"] else "old"
    return {
        "old": old_res, "new": new_res,
        "recommended": rec, "savings": abs(old_res["total_tax"] - new_res["total_tax"]),
        "trace": new_trace if rec == "new" else old_trace
    }

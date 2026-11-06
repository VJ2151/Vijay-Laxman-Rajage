"""Implementation C: Deterministic runtime interpreter for compiled declarative rules.

Executes compiled_rules.json with zero LLM dependency at query time.
Maintains full statutory traceability and T10 audit reconciliation.
"""

import json
import math
from pathlib import Path

COMPILED_RULES_PATH = Path(__file__).parent / "compiled_rules.json"


def round_to_10(val: float) -> int:
    """Sec 288A/B: Round to nearest multiple of Rs 10."""
    return int(math.floor((val + 5.0) / 10.0) * 10)


def load_rules(fy: str) -> dict:
    """Load declarative rules for specified financial year."""
    with open(COMPILED_RULES_PATH, "r", encoding="utf-8") as f:
        all_rules = json.load(f)
    if fy not in all_rules:
        raise ValueError(f"No compiled rules found for financial year: {fy}")
    return all_rules[fy]


def _calc_slab_tax_compiled(taxable: float, slabs: list) -> tuple[float, str]:
    """Evaluate tax slab list deterministically."""
    if taxable <= 0:
        return 0.0, slabs[0]["clause_id"]
    tax, rem = 0.0, taxable
    active_clause = slabs[0]["clause_id"]
    for s in slabs:
        lower = s["lower"]
        upper = s["upper"]
        rate = s["rate"]
        clause = s["clause_id"]
        if upper is not None:
            span_size = upper - lower
            span = min(rem, span_size)
            tax += span * rate
            rem -= span
        else:
            tax += rem * rate
            rem = 0
        if rem <= 0:
            active_clause = clause
            break
    return tax, active_clause


def _calc_regime_compiled(inputs: dict, regime: str, rules: dict) -> tuple[dict, list[dict]]:
    """Compute tax for single regime using compiled rules and generate T10 trace."""
    gross = float(inputs.get("gross_salary", 0.0))
    age = int(inputs.get("age", 30))
    trace = [{"label": "Gross Salary", "amount": gross, "clause_id": "GROSS-SALARY", "kind": "income"}]
    deductions_breakdown = {}

    if regime == "new":
        std_rule = rules["standard_deductions"]["new"]
        std_ded = min(gross, float(std_rule["amount"]))
        deductions_breakdown["standard_deduction"] = std_ded
        trace.append({"label": "Standard Deduction", "amount": std_ded, "clause_id": std_rule["clause_id"], "kind": "deduction"})
        taxable_raw = max(0.0, gross - std_ded)
        slabs = rules["slabs"]["new"]
    else:
        std_rule = rules["standard_deductions"]["old"]
        std_ded = min(gross, float(std_rule["amount"]))
        # HRA
        basic = float(inputs.get("basic", 0.0))
        hra_rec = float(inputs.get("hra_received", 0.0))
        rent = float(inputs.get("rent_paid", 0.0))
        metro = bool(inputs.get("metro", False))
        excess_rent = max(0.0, rent - 0.10 * basic) if (hra_rec > 0 and rent > 0) else 0.0
        metro_lim = (0.50 if metro else 0.40) * basic
        hra_exemp = min(hra_rec, excess_rent, metro_lim) if (hra_rec > 0 and rent > 0) else 0.0

        sal_net = max(0.0, gross - hra_exemp - std_ded)
        sec24_cap = float(rules["deductions"]["sec24b"]["cap"])
        home_int = min(sec24_cap, float(inputs.get("home_loan_interest", 0.0)))
        inc_after_hp = max(0.0, sal_net - home_int)

        # Chapter VI-A
        c80 = min(float(rules["deductions"]["sec80c"]["cap"]), float(inputs.get("sec80c", 0.0)))
        ccd = min(float(rules["deductions"]["sec80ccd1b"]["cap"]), float(inputs.get("sec80ccd1b", 0.0)))
        d_self_cap = float(rules["deductions"]["sec80d_self"]["senior_cap"] if age >= 60 else rules["deductions"]["sec80d_self"]["cap"])
        d_self = min(d_self_cap, float(inputs.get("sec80d_self", 0.0)))
        d_par_cap = float(rules["deductions"]["sec80d_parents"]["senior_cap"] if inputs.get("parents_senior", False) else rules["deductions"]["sec80d_parents"]["cap"])
        d_parents = min(d_par_cap, float(inputs.get("sec80d_parents", 0.0)))
        taxable_raw = max(0.0, inc_after_hp - (c80 + ccd + d_self + d_parents))

        ded_items = [
            ("hra_exemption", hra_exemp, rules["deductions"]["hra"]["clause_id"], "exemption"),
            ("standard_deduction", std_ded, std_rule["clause_id"], "deduction"),
            ("home_loan_interest", home_int, rules["deductions"]["sec24b"]["clause_id"], "deduction"),
            ("sec80c", c80, rules["deductions"]["sec80c"]["clause_id"], "deduction"),
            ("sec80ccd1b", ccd, rules["deductions"]["sec80ccd1b"]["clause_id"], "deduction"),
            ("sec80d_self", d_self, rules["deductions"]["sec80d_self"]["clause_id"], "deduction"),
            ("sec80d_parents", d_parents, rules["deductions"]["sec80d_parents"]["clause_id"], "deduction")
        ]
        for k, v, cid, kd in ded_items:
            deductions_breakdown[k] = v
            trace.append({"label": k.replace("_", " ").title(), "amount": v, "clause_id": cid, "kind": kd})

        slabs = rules["slabs"]["old_super"] if age >= 80 else (rules["slabs"]["old_senior"] if age >= 60 else rules["slabs"]["old_normal"])

    taxable = round_to_10(taxable_raw)
    round_diff = round(taxable - taxable_raw, 2)
    rnd_clause = rules["rounding"]["income_clause_id"]
    if round_diff > 0:
        trace.append({"label": "Sec 288A Rounding Add", "amount": round_diff, "clause_id": rnd_clause, "kind": "income_add"})
    elif round_diff < 0:
        trace.append({"label": "Sec 288A Rounding Sub", "amount": abs(round_diff), "clause_id": rnd_clause, "kind": "income_sub"})

    slab_tax, slab_clause = _calc_slab_tax_compiled(taxable, slabs)
    trace.append({"label": "Slab Tax", "amount": slab_tax, "clause_id": slab_clause, "kind": "tax_add"})

    # Rebate 87A
    rebate_cfg = rules["rebate_87a"][regime]
    rebate, mr_87a = 0.0, 0.0
    if taxable <= rebate_cfg["limit"]:
        rebate = min(slab_tax, float(rebate_cfg["max_rebate"]))
    elif rebate_cfg.get("marginal_relief"):
        excess = taxable - rebate_cfg["limit"]
        if slab_tax > excess:
            mr_87a = slab_tax - excess
            rebate = mr_87a

    if rebate > 0:
        trace.append({"label": "Section 87A Rebate", "amount": rebate, "clause_id": rebate_cfg["clause_id"], "kind": "tax_sub"})

    tax_after_reb = max(0.0, slab_tax - rebate)

    # Surcharge
    surch_cfg = rules["surcharge"][regime]
    raw_surch, mr_surch, net_surch = 0.0, 0.0, 0.0
    if taxable > 5000000:
        act_t, act_r = 0, 0.0
        for th in surch_cfg["thresholds"]:
            if taxable > th["thresh"]:
                act_t, act_r = th["thresh"], th["rate"]
        raw_surch = tax_after_reb * act_r
        tax_at_t, _ = _calc_slab_tax_compiled(float(act_t), slabs)
        thresh_r = 0.10 if act_t == 10000000 else (0.15 if act_t == 20000000 else (0.25 if act_t == 50000000 else 0.0))
        max_tax_surch = tax_at_t * (1.0 + thresh_r) + (taxable - act_t)
        curr_tax_surch = tax_after_reb + raw_surch
        if curr_tax_surch > max_tax_surch:
            mr_surch = curr_tax_surch - max_tax_surch
            net_surch = max(0.0, raw_surch - mr_surch)
        else:
            net_surch = raw_surch

    if raw_surch > 0:
        trace.append({"label": "Surcharge", "amount": raw_surch, "clause_id": surch_cfg["clause_id"], "kind": "tax_add"})
    if mr_surch > 0:
        trace.append({"label": "Surcharge Marginal Relief", "amount": mr_surch, "clause_id": surch_cfg["relief_clause_id"], "kind": "tax_sub"})

    cess_rate = float(rules["cess"]["rate"])
    cess_raw = (tax_after_reb + net_surch) * cess_rate
    trace.append({"label": "Health & Education Cess (4%)", "amount": cess_raw, "clause_id": rules["cess"]["clause_id"], "kind": "tax_add"})

    total_tax = round_to_10(tax_after_reb + net_surch + cess_raw)
    tax_round_diff = round(total_tax - (tax_after_reb + net_surch + cess_raw), 2)
    t_rnd_clause = rules["rounding"]["tax_clause_id"]
    if tax_round_diff > 0:
        trace.append({"label": "Sec 288B Rounding Add", "amount": tax_round_diff, "clause_id": t_rnd_clause, "kind": "tax_add"})
    elif tax_round_diff < 0:
        trace.append({"label": "Sec 288B Rounding Sub", "amount": abs(tax_round_diff), "clause_id": t_rnd_clause, "kind": "tax_sub"})

    return {
        "gross": gross, "deductions_breakdown": deductions_breakdown, "taxable_income": taxable,
        "slab_tax": slab_tax, "rebate": rebate, "surcharge": net_surch,
        "marginal_relief": mr_surch + mr_87a, "cess": cess_raw, "total_tax": total_tax
    }, trace


def calc_compiled(inputs: dict, fy: str = "2024-25") -> dict:
    """Execute compiled declarative rules."""
    rules = load_rules(fy)
    old_res, old_trace = _calc_regime_compiled(inputs, "old", rules)
    new_res, new_trace = _calc_regime_compiled(inputs, "new", rules)
    rec = "new" if new_res["total_tax"] <= old_res["total_tax"] else "old"
    return {
        "old": old_res, "new": new_res,
        "recommended": rec, "savings": abs(old_res["total_tax"] - new_res["total_tax"]),
        "trace": new_trace if rec == "new" else old_trace
    }

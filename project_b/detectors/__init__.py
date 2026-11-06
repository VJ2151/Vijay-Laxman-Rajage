"""Master detector registry mapping (problem_id, family) -> detector function."""

from project_b.detectors.llm import (
    detect_llm_a, detect_llm_b, detect_llm_c, detect_llm_d,
    detect_llm_e, detect_llm_f, detect_llm_g, detect_llm_h,
    detect_llm_i, detect_llm_j, detect_llm_k, detect_llm_l,
)
from project_b.detectors.rules import (
    detect_rule_a, detect_rule_b, detect_rule_c, detect_rule_d,
    detect_rule_e, detect_rule_f, detect_rule_g, detect_rule_h,
    detect_rule_i, detect_rule_j, detect_rule_k, detect_rule_l,
)
from project_b.detectors.stats import (
    detect_stats_a, detect_stats_b, detect_stats_c, detect_stats_d,
    detect_stats_e, detect_stats_f, detect_stats_g, detect_stats_h,
    detect_stats_i, detect_stats_j, detect_stats_k, detect_stats_l,
)

DETECTOR_REGISTRY = {
    # Family a: Rules
    ("a", "rules"): detect_rule_a,
    ("b", "rules"): detect_rule_b,
    ("c", "rules"): detect_rule_c,
    ("d", "rules"): detect_rule_d,
    ("e", "rules"): detect_rule_e,
    ("f", "rules"): detect_rule_f,
    ("g", "rules"): detect_rule_g,
    ("h", "rules"): detect_rule_h,
    ("i", "rules"): detect_rule_i,
    ("j", "rules"): detect_rule_j,
    ("k", "rules"): detect_rule_k,
    ("l", "rules"): detect_rule_l,

    # Family b: Statistical / ML
    ("a", "stats"): detect_stats_a,
    ("b", "stats"): detect_stats_b,
    ("c", "stats"): detect_stats_c,
    ("d", "stats"): detect_stats_d,
    ("e", "stats"): detect_stats_e,
    ("f", "stats"): detect_stats_f,
    ("g", "stats"): detect_stats_g,
    ("h", "stats"): detect_stats_h,
    ("i", "stats"): detect_stats_i,
    ("j", "stats"): detect_stats_j,
    ("k", "stats"): detect_stats_k,
    ("l", "stats"): detect_stats_l,

    # Family c: LLM
    ("a", "llm"): detect_llm_a,
    ("b", "llm"): detect_llm_b,
    ("c", "llm"): detect_llm_c,
    ("d", "llm"): detect_llm_d,
    ("e", "llm"): detect_llm_e,
    ("f", "llm"): detect_llm_f,
    ("g", "llm"): detect_llm_g,
    ("h", "llm"): detect_llm_h,
    ("i", "llm"): detect_llm_i,
    ("j", "llm"): detect_llm_j,
    ("k", "llm"): detect_llm_k,
    ("l", "llm"): detect_llm_l,
}


def get_detector(problem_id: str, family: str):
    """Retrieve detector from registry."""
    key = (problem_id.lower(), family.lower())
    if key not in DETECTOR_REGISTRY:
        raise ValueError(f"No detector found for problem {problem_id} and family {family}")
    return DETECTOR_REGISTRY[key]

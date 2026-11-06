"""Evaluation and unit tests for natural language parser (Task 3)."""

import json
from pathlib import Path
from project_a.parser import parse_description


def test_parser_50_descriptions():
    descs_path = Path("project_a/tests/descriptions.json")
    with open(descs_path, "r", encoding="utf-8") as f:
        descriptions = json.load(f)

    correct_clarification = 0
    total_clarification_cases = 0
    correct_extractions = 0
    total_extraction_cases = 0
    guesses_when_should_clarify = 0

    results_log = []

    for item in descriptions:
        desc_id = item["id"]
        text = item["text"]
        expected_clarify = item["expected_clarification"]

        res = parse_description(text, fy="2024-25")
        asked_clarify = (res["clarifying_question"] is not None)

        if expected_clarify:
            total_clarification_cases += 1
            if asked_clarify:
                correct_clarification += 1
            else:
                guesses_when_should_clarify += 1
        else:
            total_extraction_cases += 1
            if not asked_clarify and res["tax"] is not None:
                correct_extractions += 1

        results_log.append({
            "id": desc_id,
            "text": text,
            "expected_clarification": expected_clarify,
            "asked_clarification": asked_clarify,
            "question": res["clarifying_question"],
            "inputs": res["inputs"],
            "has_tax": res["tax"] is not None
        })

    clarification_accuracy = correct_clarification / total_clarification_cases
    extraction_accuracy = correct_extractions / total_extraction_cases
    guess_rate = guesses_when_should_clarify / total_clarification_cases

    eval_summary = {
        "total_descriptions": len(descriptions),
        "total_extraction_cases": total_extraction_cases,
        "total_clarification_cases": total_clarification_cases,
        "extraction_accuracy": round(extraction_accuracy, 4),
        "clarification_accuracy": round(clarification_accuracy, 4),
        "guess_rate": round(guess_rate, 4),
        "results": results_log
    }

    out_file = Path("results/parser_evaluation.json")
    out_file.parent.mkdir(exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)

    assert clarification_accuracy == 1.0, f"Clarification accuracy below 100%: {clarification_accuracy}"
    assert extraction_accuracy == 1.0, f"Extraction accuracy below 100%: {extraction_accuracy}"
    assert guess_rate == 0.0, f"Parser guessed when it should have clarified! Guess rate: {guess_rate}"

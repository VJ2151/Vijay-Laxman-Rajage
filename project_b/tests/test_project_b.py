"""Automated test suite for Project B (Data Quality Pipeline and Detectors).

Verifies:
- All 12 injectors (a-l) produce valid ground-truth masks/flags.
- Detectors emit conforming output schema (row_mask, batch_flag, explanation, clarity_score).
- Cascaded pipeline executes and outputs executive decisions.
"""

import numpy as np
import pandas as pd
import pytest
from project_b.injector import inject, INJECTORS
from project_b.detectors import get_detector
from project_b.detectors.rules import detect_rule_a, detect_rule_d, detect_rule_h, detect_rule_l
from project_b.pipeline import run_pipeline


@pytest.fixture
def sample_batch():
    return pd.DataFrame({
        "unique_key": ["1001", "1002", "1003", "1004", "1005"],
        "created_date": ["2023-05-01T10:00:00.000"] * 5,
        "closed_date": ["2023-05-02T10:00:00.000"] * 5,
        "agency": ["NYPD", "DOT", "DEP", "NYPD", "DSNY"],
        "complaint_type": ["Noise - Residential", "Street Condition", "Water Leak", "Blocked Driveway", "Sanitation"],
        "descriptor": ["Loud Music", "Pothole", "Leak in basement", "No Access", "Missed Collection"],
        "borough": ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"],
        "incident_zip": ["10001", "11201", "11375", "10451", "10301"],
        "latitude": [40.75, 40.69, 40.72, 40.82, 40.58],
        "longitude": [-73.99, -73.98, -73.83, -73.92, -74.15],
        "status": ["Closed", "Closed", "Closed", "Closed", "Closed"],
        "resolution_description": ["Action taken by police.", "Pothole repaired.", "Inspected.", "Summons issued.", "Collected."],
        "council_district": [1, 33, 29, 17, 49]
    })


def test_all_injectors_produce_ground_truth(sample_batch):
    for pid in INJECTORS:
        corr, gt = inject(sample_batch, pid, rate=0.2, seed=42)
        assert len(corr) >= len(sample_batch)
        if pid in ["a", "b", "c", "g"]:
            assert isinstance(gt, bool)
            assert gt is True
        else:
            assert isinstance(gt, pd.Series)
            assert gt.dtype == bool
            assert gt.sum() > 0


def test_rule_detectors_schema(sample_batch):
    for pid in ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]:
        det = get_detector(pid, "rules")
        res = det(sample_batch)
        assert "batch_flag" in res
        assert "row_mask" in res
        assert "explanation" in res
        assert "clarity_score" in res
        assert isinstance(res["batch_flag"], (bool, np.bool_))


def test_rule_temporal_and_pii_detection(sample_batch):
    # Test temporal inversion
    corr_h, gt_h = inject(sample_batch, "h", rate=1.0, seed=42)
    res_h = detect_rule_h(corr_h)
    assert res_h["batch_flag"] is True
    assert (res_h["row_mask"] & gt_h).sum() == len(sample_batch)

    # Test synthetic PII injection & detection
    corr_l, gt_l = inject(sample_batch, "l", rate=1.0, seed=42)
    res_l = detect_rule_l(corr_l)
    assert res_l["batch_flag"] is True
    assert res_l["row_mask"].sum() > 0


def test_pipeline_execution(sample_batch):
    res = run_pipeline(sample_batch, batch_id="TEST_HEALTHY")
    assert res["status"] == "HEALTHY_PASSED"
    assert res["health_pct"] == 100.0
    assert "alert_summary" in res

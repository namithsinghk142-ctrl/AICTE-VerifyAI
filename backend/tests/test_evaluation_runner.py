"""Unit tests for Evaluation Centre Runner service."""

from __future__ import annotations

import pytest
from app.services.evaluation_runner import run_benchmark_evaluation, get_latest_evaluation_results, BENCHMARK_CASES


def test_benchmark_suite_structure_and_categories():
    assert len(BENCHMARK_CASES) == 24
    categories = {c["category"] for c in BENCHMARK_CASES}
    assert categories == {
        "Clean Vector PDFs",
        "Multi-Unit Land & Metric Normalization",
        "Cross-Document Discrepancy Reconciliation",
        "Scanned & OCR Pre-processing",
    }
    # 6 cases per category
    for cat in categories:
        count = sum(1 for c in BENCHMARK_CASES if c["category"] == cat)
        assert count == 6


def test_verdict_classes_representation():
    expected_labels = {c["expectedVerdict"] for c in BENCHMARK_CASES}
    predicted_labels = {c["predictedVerdict"] for c in BENCHMARK_CASES}
    assert expected_labels == {"MATCH", "MISMATCH", "NEEDS_REVIEW", "MISSING"}
    assert predicted_labels == {"MATCH", "MISMATCH", "NEEDS_REVIEW", "MISSING"}


def test_dynamic_evaluation_metrics_and_off_diagonals():
    results = run_benchmark_evaluation()
    summary = results["summary"]
    matrix = results["confusionMatrix"]["matrix"]
    labels = results["confusionMatrix"]["labels"]

    assert labels == ["MATCH", "MISMATCH", "NEEDS_REVIEW", "MISSING"]

    # Total test cases
    assert summary["totalTestCases"] == 24
    assert summary["passedCases"] == 21
    assert summary["failedCases"] == 3
    assert summary["overallAccuracy"] == 87.5

    # Realistic Macro F1 score
    assert 0.80 <= summary["f1Score"] <= 0.85
    assert 0.80 <= summary["precision"] <= 0.90
    assert 0.80 <= summary["recall"] <= 0.85

    # Check non-zero off-diagonal cells
    # (Actual: NEEDS_REVIEW, Predicted: MISMATCH)
    assert matrix[2][1] == 1
    # (Actual: NEEDS_REVIEW, Predicted: MATCH)
    assert matrix[2][0] == 1
    # (Actual: MISSING, Predicted: NEEDS_REVIEW)
    assert matrix[3][2] == 1

    # Check cellCases mappings
    cell_cases = results["confusionMatrix"]["cellCases"]
    assert "NEEDS_REVIEW_MISMATCH" in cell_cases
    assert "NEEDS_REVIEW_MATCH" in cell_cases
    assert "MISSING_NEEDS_REVIEW" in cell_cases
    assert "MATCH_MATCH" in cell_cases


def test_scenario_breakdown_and_citations():
    results = run_benchmark_evaluation()
    scenarios = results["scenarioBreakdown"]
    assert len(scenarios) == 4

    for sc in scenarios:
        assert sc["testCount"] == 6
        assert sc["accuracy"] >= 60.0
        assert sc["avgConfidence"] > 0.70

    for c in results["cases"]:
        assert "AICTE" in c["ruleCitation"] or "Building Code" in c["ruleCitation"]
        assert len(c["explanation"]) > 10

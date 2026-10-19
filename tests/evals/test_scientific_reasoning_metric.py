"""Tests for the public scientific reasoning metric adapter."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from deepeval.test_case import LLMTestCase

from tests.evals.metrics import build_metrics
from tests.evals.scientific_reasoning_metric import ScientificReasoningMetric


def test_metric_passes_evidence_to_judge():
    """Check that the adapter forwards the question, answer, and evidence."""
    judgment = SimpleNamespace(
        normalized_score=1.0,
        reason="Supported by evidence",
        unsupported_claims=[],
    )
    judge = Mock(return_value=judgment)
    metric = ScientificReasoningMetric(
        evidence="Example evidence",
        judge=judge,
    )

    score = metric.measure(
        LLMTestCase(input="Example question", actual_output="Example answer")
    )

    assert score == 1.0
    assert metric.is_successful()
    judge.assert_called_once_with(
        question="Example question",
        answer="Example answer",
        evidence="Example evidence",
    )


def test_metric_rejects_low_score():
    """Check that an insufficient score fails the threshold."""
    judge = Mock(return_value=SimpleNamespace(
        normalized_score=0.5,
        reason="Incomplete reasoning",
        unsupported_claims=["Example unsupported claim"],
    ))
    metric = ScientificReasoningMetric(
        evidence="Example evidence",
        judge=judge,
        threshold=1.0,
    )

    assert metric.measure(
        LLMTestCase(input="Question", actual_output="Answer")
    ) == 0.5
    assert not metric.is_successful()
    assert "Example unsupported claim" in metric.reason


def test_factory_requires_judge():
    """Reject scientific metrics without an evaluator."""
    with pytest.raises(ValueError, match="requires scientific_judge"):
        build_metrics([{
            "metric": "ScientificReasoningMetric",
            "evidence": "Example evidence",
        }])


def test_factory_creates_metric():
    """Check that the metric registry accepts an injected judge."""
    judge = Mock()
    metrics = build_metrics(
        [{
            "metric": "ScientificReasoningMetric",
            "evidence": "Example evidence",
        }],
        scientific_judge=judge,
    )

    assert len(metrics) == 1
    assert isinstance(metrics[0], ScientificReasoningMetric)
    assert metrics[0].judge is judge

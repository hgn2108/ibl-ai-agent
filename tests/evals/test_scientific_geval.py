"""Offline tests for configurable scientific GEval metrics."""

from unittest.mock import Mock, patch

import pytest
from deepeval.test_case import LLMTestCase, SingleTurnParams

from tests.evals.scientific_geval import (
    GENERAL_SCIENTIFIC_CRITERIA,
    build_scientific_geval,
)


def test_general_criteria_baseline():
    """Use fixed general criteria when no custom settings are supplied."""
    evaluator = Mock()

    with patch("tests.evals.scientific_geval.GEval") as geval:
        build_scientific_geval(evaluator=evaluator)

    kwargs = geval.call_args.kwargs
    assert kwargs["criteria"] == GENERAL_SCIENTIFIC_CRITERIA
    assert kwargs["evaluation_steps"] is None
    assert kwargs["model"] is evaluator


def test_custom_criteria():
    """Pass custom scientific criteria to GEval."""
    criteria = "Evaluate whether conclusions follow from the evidence."

    with patch("tests.evals.scientific_geval.GEval") as geval:
        build_scientific_geval(evaluator=Mock(), criteria=criteria)

    assert geval.call_args.kwargs["criteria"] == criteria
    assert geval.call_args.kwargs["evaluation_steps"] is None


def test_explicit_evaluation_steps():
    """Pass predefined evaluation steps without generated criteria."""
    steps = [
        "Identify the claims made in the answer.",
        "Check each claim against the evidence.",
        "Penalize unsupported conclusions.",
    ]

    with patch("tests.evals.scientific_geval.GEval") as geval:
        build_scientific_geval(
            evaluator=Mock(),
            evaluation_steps=steps,
        )

    kwargs = geval.call_args.kwargs
    assert kwargs["criteria"] is None
    assert kwargs["evaluation_steps"] == steps


def test_evaluation_parameters():
    """Include the question, answer, and supporting evidence."""
    with patch("tests.evals.scientific_geval.GEval") as geval:
        build_scientific_geval(evaluator=Mock())

    assert geval.call_args.kwargs["evaluation_params"] == [
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ]


def test_evidence_in_test_case():
    """Keep evidence separate from the answer and criteria."""
    case = LLMTestCase(
        input="What color is the sample?",
        actual_output="The sample is blue.",
        retrieval_context=["The sample is blue."],
    )
    assert case.retrieval_context == ["The sample is blue."]


@pytest.mark.parametrize("criteria", ["", "   "])
def test_empty_criteria_rejected(criteria):
    """Reject empty custom criteria."""
    with pytest.raises(ValueError, match="criteria"):
        build_scientific_geval(evaluator=Mock(), criteria=criteria)


@pytest.mark.parametrize("steps", [[], [""], ["Valid step", "   "]])
def test_invalid_steps_rejected(steps):
    """Reject empty evaluation steps."""
    with pytest.raises(ValueError, match="steps"):
        build_scientific_geval(evaluator=Mock(), evaluation_steps=steps)


def test_criteria_and_steps_rejected():
    """Require a single evaluation configuration."""
    with pytest.raises(ValueError, match="criteria or evaluation_steps"):
        build_scientific_geval(
            evaluator=Mock(),
            criteria="Check accuracy.",
            evaluation_steps=["Check evidence."],
        )


def test_missing_evaluator_rejected():
    """Avoid accidentally using DeepEval's default model."""
    with pytest.raises(ValueError, match="evaluator"):
        build_scientific_geval(evaluator=None)


@pytest.mark.parametrize("threshold", [-0.1, 1.1])
def test_invalid_threshold_rejected(threshold):
    """Require normalized thresholds between zero and one."""
    with pytest.raises(ValueError, match="Threshold"):
        build_scientific_geval(evaluator=Mock(), threshold=threshold)

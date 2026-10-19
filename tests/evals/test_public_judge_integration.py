"""Offline integration tests for the custom judge and DeepEval metric."""

from __future__ import annotations

import json

import pytest
from deepeval.test_case import LLMTestCase

from tests.evals.custom_llm_judge import judge_answer
from tests.evals.scientific_reasoning_metric import ScientificReasoningMetric


def example_prompt_builder(
    question: str,
    answer: str,
    evidence: str,
) -> str:
    """Build a public demonstration prompt, not the private rubric."""
    return (
        "This is a demonstration of a configurable evaluation prompt.\n"
        "Assign score 2 when the answer agrees with the evidence, "
        "score 1 for partial agreement, and score 0 for disagreement.\n"
        "Return JSON with score, reason, and unsupported_claims.\n"
        f"Question: {question}\n"
        f"Evidence: {evidence}\n"
        f"Answer: {answer}\n"
    )


@pytest.mark.parametrize(
    ("raw_score", "expected_score", "expected_pass"),
    [
        (0, 0.0, False),
        (1, 0.5, False),
        (2, 1.0, True),
    ],
)
def test_public_integration(
    raw_score: int,
    expected_score: float,
    expected_pass: bool,
) -> None:
    """Connect the custom judge to DeepEval without external calls."""
    question = "What color is the sample?"
    answer = "The sample is blue."
    evidence = "The sample is blue."

    calls: list[str] = []

    def mock_generate(prompt: str) -> str:
        calls.append(prompt)
        return json.dumps(
            {
                "score": raw_score,
                "reason": "Demonstration judgment.",
                "unsupported_claims": [],
            }
        )

    def configured_judge(
        question: str,
        answer: str,
        evidence: str,
    ):
        return judge_answer(
            question=question,
            answer=answer,
            evidence=evidence,
            prompt_builder=example_prompt_builder,
            generate=mock_generate,
        )

    metric = ScientificReasoningMetric(
        evidence=evidence,
        judge=configured_judge,
        threshold=1.0,
    )

    test_case = LLMTestCase(
        input=question,
        actual_output=answer,
    )

    score = metric.measure(test_case)

    assert score == expected_score
    assert metric.score == expected_score
    assert metric.is_successful() is expected_pass
    assert metric.judgment is not None
    assert metric.judgment.score == raw_score
    assert len(calls) == 1
    assert question in calls[0]
    assert answer in calls[0]
    assert evidence in calls[0]


def test_unsupported_claims_reach_metric_reason() -> None:
    """Check that unsupported claims remain visible in DeepEval."""

    def mock_generate(prompt: str) -> str:
        return json.dumps(
            {
                "score": 0,
                "reason": "The statement is unsupported.",
                "unsupported_claims": ["The sample is green."],
            }
        )

    def configured_judge(
        question: str,
        answer: str,
        evidence: str,
    ):
        return judge_answer(
            question=question,
            answer=answer,
            evidence=evidence,
            prompt_builder=example_prompt_builder,
            generate=mock_generate,
        )

    metric = ScientificReasoningMetric(
        evidence="The sample is blue.",
        judge=configured_judge,
    )

    metric.measure(
        LLMTestCase(
            input="What color is the sample?",
            actual_output="The sample is green.",
        )
    )

    assert metric.score == 0.0
    assert not metric.is_successful()
    assert "The sample is green." in metric.reason

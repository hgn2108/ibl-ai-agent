"""DeepEval adapter for an externally supplied scientific reasoning judge."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class Judgment(Protocol):
    """Expected interface of a scientific judge result."""

    normalized_score: float
    reason: str
    unsupported_claims: list[str]


Judge = Callable[..., Judgment]


class ScientificReasoningMetric(BaseMetric):
    """Evaluate scientific reasoning using an externally supplied judge."""

    name = "ScientificReasoningMetric"

    def __init__(
        self,
        evidence: str,
        judge: Judge,
        threshold: float = 1.0,
    ) -> None:
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")

        self.evidence = evidence
        self.judge = judge
        self.threshold = threshold
        self.score = 0.0
        self.reason = "Not evaluated"
        self.success = False
        self.judgment: Judgment | None = None

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        """Score an answer using the supplied evidence and judge."""
        self.score = 0.0
        self.reason = "Not evaluated"
        self.success = False
        self.judgment = None

        judgment = self.judge(
            question=test_case.input,
            answer=test_case.actual_output,
            evidence=self.evidence,
        )
        self.judgment = judgment
        self.score = judgment.normalized_score
        self.reason = judgment.reason

        if judgment.unsupported_claims:
            self.reason += (
                "; Unsupported claims: "
                + "; ".join(judgment.unsupported_claims)
            )

        self.success = self.is_successful()
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        """Evaluate asynchronously using the synchronous judge."""
        return self.measure(test_case, *args, **kwargs)

    def is_successful(self) -> bool:
        """Return whether the score meets the threshold."""
        return self.judgment is not None and self.score >= self.threshold

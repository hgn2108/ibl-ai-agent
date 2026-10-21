"""Inspect scorer that delegates scientific-reasoning grading to an external judge.

The judge, its rubric and the reference answers live outside this repository; it is
injected as a callable, so only the adapter is public.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from inspect_ai.scorer import Score, accuracy, scorer, stderr


class Judgment(Protocol):
    """Expected result of a scientific judge."""

    normalized_score: float
    reason: str
    unsupported_claims: list[str]


Judge = Callable[..., Awaitable[Judgment]]


@scorer(metrics=[accuracy(), stderr()])
def scientific_reasoning(judge: Judge, evidence: str, threshold: float = 1.0):
    """Score a reply with ``judge``; pass when its normalized score reaches ``threshold``.

    Parameters
    ----------
    judge
        Async, called as ``judge(question=, answer=, evidence=)``; returns a `Judgment`.
    evidence
        Supporting evidence the judge checks the reply's claims against.
    threshold
        Minimum normalized score (0-1) that counts as a pass.
    """
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")

    async def score(state, target):
        judgment = await judge(
            question=state.input_text, answer=state.output.completion, evidence=evidence
        )
        explanation = judgment.reason
        if judgment.unsupported_claims:
            explanation += "; Unsupported claims: " + "; ".join(judgment.unsupported_claims)
        return Score(
            value=int(judgment.normalized_score >= threshold),
            answer=state.output.completion,
            explanation=explanation,
            metadata={"normalized_score": judgment.normalized_score},
        )

    return score

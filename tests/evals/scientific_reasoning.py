"""Inspect scorer: an LLM judge grades a reply 0-2 against evidence, with a private rubric.

The rubric lives outside this repository and is supplied as a ``prompt_builder``;
the sample's ``target`` carries the evidence the reply is checked against.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from inspect_ai.model import Model, get_model
from inspect_ai.scorer import Score, accuracy, scorer, stderr
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Judgment(BaseModel):
    """Judge result; any extra, missing or mistyped field is rejected."""

    model_config = ConfigDict(extra="forbid", strict=True)

    score: Literal[0, 1, 2]
    reason: str = Field(min_length=1)
    unsupported_claims: list[str]

    @property
    def normalized_score(self) -> float:
        """Score scaled to [0, 1]."""
        return self.score / 2


@scorer(metrics=[accuracy(), stderr()])
def scientific_reasoning(
    prompt_builder: Callable[[str, str, str], str],
    model: str | Model = "anthropic/claude-sonnet-5-5",
    threshold: float = 1.0,
):
    """Judge each reply with ``model``; pass when its normalized score reaches ``threshold``.

    Parameters
    ----------
    prompt_builder
        ``(question, answer, evidence) -> prompt``; holds the (private) rubric and
        must ask for a JSON object with ``score`` (0, 1 or 2), ``reason`` and
        ``unsupported_claims``.
    model
        Judge, as an Inspect model id or `Model`. A malformed reply is retried once.
    threshold
        Minimum normalized score (0-1) that counts as a pass.
    """
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    judge = get_model(model)

    async def score(state, target):
        if not target.text.strip():
            raise ValueError("Evidence (the sample target) must not be empty")
        answer = state.output.completion
        prompt = prompt_builder(state.input_text, answer, target.text)
        for attempt in range(2):
            try:
                judgment = Judgment.model_validate_json((await judge.generate(prompt)).completion)
                break
            except ValidationError as exc:
                if attempt:
                    raise ValueError("Judge returned an invalid response after 2 attempts") from exc
        explanation = judgment.reason
        if judgment.unsupported_claims:
            explanation += "; Unsupported claims: " + "; ".join(judgment.unsupported_claims)
        return Score(
            value=int(judgment.normalized_score >= threshold),
            answer=answer,
            explanation=explanation,
            metadata={"normalized_score": judgment.normalized_score},
        )

    return score

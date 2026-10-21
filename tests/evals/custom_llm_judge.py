"""LLM judge that scores an answer 0-2 against evidence, with a caller-supplied rubric."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from inspect_ai.model import get_model
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


async def judge_answer(
    question: str,
    answer: str,
    evidence: str,
    prompt_builder: Callable[[str, str, str], str],
    generate: Callable[[str], Awaitable[str]] | None = None,
    model: str = "anthropic/claude-sonnet-5-5",
) -> Judgment:
    """Judge ``answer`` against ``evidence``, retrying once on a malformed reply.

    Parameters
    ----------
    prompt_builder
        ``(question, answer, evidence) -> prompt``; holds the (private) rubric and
        must ask for a JSON object with ``score``, ``reason`` and ``unsupported_claims``.
    generate
        Async ``prompt -> reply text``. Defaults to an Inspect ``model`` call.
    model
        Inspect model id of the judge, used when ``generate`` is None.
    """
    if not evidence.strip():
        raise ValueError("Evidence must not be empty")
    if generate is None:

        async def generate(prompt: str) -> str:
            return (await get_model(model).generate(prompt)).completion

    prompt = prompt_builder(question, answer, evidence)
    for attempt in range(2):
        try:
            return Judgment.model_validate_json(await generate(prompt))
        except ValidationError as exc:
            if attempt:
                raise ValueError("Judge returned an invalid response after 2 attempts") from exc

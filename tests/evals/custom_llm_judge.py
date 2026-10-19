"""Reusable LLM judge with externally supplied evaluation instructions."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Judgment:
    """Validated judge result with a normalized score."""

    score: int
    reason: str
    unsupported_claims: list[str]

    @property
    def normalized_score(self) -> float:
        """Return the score normalized to [0, 1]."""
        return self.score / 2.0


def parse_judgment(raw: str) -> Judgment:
    """Parse and strictly validate a JSON judge response."""
    try:
        obj = json.loads(raw.strip())
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Judge did not return valid JSON") from exc

    if not isinstance(obj, dict) or set(obj) != {
        "score",
        "reason",
        "unsupported_claims",
    }:
        raise ValueError("Judge JSON has invalid fields")

    if type(obj["score"]) is not int or obj["score"] not in (0, 1, 2):
        raise ValueError("Judge score must be integer 0, 1, or 2")

    if not isinstance(obj["reason"], str) or not obj["reason"].strip():
        raise ValueError("Judge reason must be nonempty text")

    claims = obj["unsupported_claims"]
    if not isinstance(claims, list) or not all(
        isinstance(x, str) and bool(x.strip()) for x in claims
    ):
        raise ValueError("Unsupported claims must be nonempty strings")

    return Judgment(
        score=obj["score"],
        reason=obj["reason"],
        unsupported_claims=claims,
    )


def claude_cli_generate(
    prompt: str,
    model: str = "sonnet",
    timeout: int = 120,
) -> str:
    """Generate a response using Claude CLI with tools disabled."""
    result = subprocess.run(
        [
            "claude",
            "-p",
            prompt,
            "--model",
            model,
            "--tools",
            "",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
    )
    return result.stdout


def judge_answer(
    question: str,
    answer: str,
    evidence: str,
    prompt_builder: Callable[[str, str, str], str],
    generate: Callable[[str], str] | None = None,
    model: str = "sonnet",
) -> Judgment:
    """Judge an answer using a configurable Claude model.

    Retry once for malformed responses. A custom generator
    can be supplied for testing or other model providers.
    """
    if not evidence.strip():
        raise ValueError("Evidence must not be empty")

    prompt = prompt_builder(question, answer, evidence)

    if generate is None:

        def generator(prompt: str) -> str:
            return claude_cli_generate(prompt, model=model)

    else:
        generator = generate

    for attempt in range(2):
        response = generator(prompt)

        try:
            return parse_judgment(response)
        except ValueError as exc:
            if attempt == 1:
                raise ValueError("Judge returned an invalid response after 2 attempts") from exc

    raise RuntimeError("Unreachable judge state")

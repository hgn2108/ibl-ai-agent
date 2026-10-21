"""Judge and scorer wired together by dependency injection, with a fake model."""

import asyncio
import json
from functools import partial
from types import SimpleNamespace

import pytest

pytest.importorskip("inspect_ai")

from tests.evals.custom_llm_judge import judge_answer  # noqa: E402
from tests.evals.scientific_reasoning import scientific_reasoning  # noqa: E402


def example_prompt_builder(question, answer, evidence):
    """Public demonstration prompt, not the private rubric."""
    return (
        "Score 2 if the answer agrees with the evidence, 1 for partial agreement, 0 otherwise. "
        "Return JSON with score, reason and unsupported_claims.\n"
        f"Question: {question}\nEvidence: {evidence}\nAnswer: {answer}"
    )


def run(score, claims=()):
    """Score one reply through scorer -> judge_answer -> fake generator."""
    prompts = []

    async def generate(prompt):
        prompts.append(prompt)
        return json.dumps({"score": score, "reason": "demo", "unsupported_claims": list(claims)})

    judge = partial(judge_answer, prompt_builder=example_prompt_builder, generate=generate)
    state = SimpleNamespace(input_text="Q", output=SimpleNamespace(completion="A"))
    result = asyncio.run(scientific_reasoning(judge, "E")(state, None))
    return result, prompts


@pytest.mark.parametrize(("score", "passed"), [(0, 0), (1, 0), (2, 1)])
def test_score_levels_map_to_pass_fail(score, passed):
    result, prompts = run(score)
    assert result.value == passed
    assert result.metadata["normalized_score"] == score / 2
    assert all(text in prompts[0] for text in ("Q", "A", "E"))


def test_unsupported_claims_reach_the_explanation():
    assert "The sample is green." in run(0, ["The sample is green."])[0].explanation

"""LLM judge with a fake generator. No API calls."""

import asyncio
import json

import pytest

pytest.importorskip("inspect_ai")

from tests.evals.custom_llm_judge import judge_answer  # noqa: E402


def reply(score=2, **over):
    return json.dumps({"score": score, "reason": "ok", "unsupported_claims": [], **over})


def judge(*replies, evidence="E"):
    """Run ``judge_answer`` on a generator that returns ``replies`` in turn."""
    prompts, queue = [], list(replies)

    async def generate(prompt):
        prompts.append(prompt)
        return queue.pop(0)

    builder = lambda q, a, e: f"{q}|{a}|{e}"  # noqa: E731
    result = asyncio.run(judge_answer("Q", "A", evidence, builder, generate))
    return result, prompts


@pytest.mark.parametrize("score", [0, 1, 2])
def test_valid_scores_are_normalized(score):
    result, prompts = judge(reply(score))
    assert result.normalized_score == score / 2
    assert prompts == ["Q|A|E"]


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        reply(3),
        reply("2"),
        reply(reason=""),
        reply(extra=1),
        '{"score": 1}',
    ],
)
def test_invalid_replies_are_rejected_after_one_retry(raw):
    with pytest.raises(ValueError, match="2 attempts"):
        judge(raw, raw)


def test_retry_recovers_from_one_bad_reply():
    result, prompts = judge("oops", reply(1))
    assert result.score == 1 and len(prompts) == 2


def test_empty_evidence_is_rejected():
    with pytest.raises(ValueError, match="Evidence"):
        judge(reply(), evidence=" ")

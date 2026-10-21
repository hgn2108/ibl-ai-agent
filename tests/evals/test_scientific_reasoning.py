"""Scientific-reasoning scorer with a mock judge model. No API calls."""

import asyncio
import json
from types import SimpleNamespace

import pytest

pytest.importorskip("inspect_ai")

from inspect_ai.model import ModelOutput, get_model  # noqa: E402

from tests.evals.scientific_reasoning import scientific_reasoning  # noqa: E402


def reply(score=2, **over):
    return json.dumps({"score": score, "reason": "ok", "unsupported_claims": [], **over})


def grade(*replies, evidence="E", **kwargs):
    """Score one reply with a mock judge that answers ``replies`` in turn."""
    outputs = [ModelOutput.from_content("mockllm/model", text) for text in replies]
    model = get_model("mockllm/model", custom_outputs=outputs)
    state = SimpleNamespace(input_text="Q", output=SimpleNamespace(completion="A"))
    prompts = []

    def builder(question, answer, evidence):
        prompts.append((question, answer, evidence))
        return "prompt"

    score = scientific_reasoning(builder, model, **kwargs)
    return asyncio.run(score(state, SimpleNamespace(text=evidence))), prompts


@pytest.mark.parametrize(("score", "passed"), [(0, 0), (1, 0), (2, 1)])
def test_score_levels_map_to_pass_fail(score, passed):
    result, prompts = grade(reply(score))
    assert result.value == passed
    assert result.metadata["normalized_score"] == score / 2
    assert prompts == [("Q", "A", "E")]


def test_threshold_is_configurable_and_validated():
    assert grade(reply(1), threshold=0.5)[0].value == 1
    with pytest.raises(ValueError, match="between 0 and 1"):
        scientific_reasoning(lambda *a: "", threshold=2)


def test_unsupported_claims_reach_the_explanation():
    result, _ = grade(reply(0, unsupported_claims=["The sample is green."]))
    assert "The sample is green." in result.explanation


@pytest.mark.parametrize(
    "raw",
    ["not json", reply(3), reply("2"), reply(reason=""), reply(extra=1), '{"score": 1}'],
)
def test_invalid_replies_are_rejected_after_one_retry(raw):
    with pytest.raises(ValueError, match="2 attempts"):
        grade(raw, raw)


def test_retry_recovers_from_one_bad_reply():
    assert grade("oops", reply(2))[0].value == 1


def test_empty_evidence_is_rejected():
    with pytest.raises(ValueError, match="Evidence"):
        grade(reply(), evidence=" ")

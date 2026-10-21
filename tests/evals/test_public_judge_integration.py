"""A public example rubric driving the scorer end to end, with a mock judge model."""

import asyncio
import json
from types import SimpleNamespace

import pytest

pytest.importorskip("inspect_ai")

from inspect_ai.model import ModelOutput, get_model  # noqa: E402

from tests.evals.scientific_reasoning import scientific_reasoning  # noqa: E402


def example_prompt_builder(question, answer, evidence):
    """Public demonstration prompt, not the private rubric."""
    return (
        "Score 2 if the answer agrees with the evidence, 1 for partial agreement, 0 otherwise. "
        "Return JSON with score, reason and unsupported_claims.\n"
        f"Question: {question}\nEvidence: {evidence}\nAnswer: {answer}"
    )


def test_example_rubric_scores_a_reply_end_to_end():
    prompts = []

    def recording_builder(*args):
        prompts.append(example_prompt_builder(*args))
        return prompts[-1]

    verdict = json.dumps({"score": 2, "reason": "Matches.", "unsupported_claims": []})
    model = get_model(
        "mockllm/model", custom_outputs=[ModelOutput.from_content("mockllm/model", verdict)]
    )
    state = SimpleNamespace(input_text="What color?", output=SimpleNamespace(completion="Blue."))
    scorer = scientific_reasoning(recording_builder, model)
    result = asyncio.run(scorer(state, SimpleNamespace(text="Ref: blue.")))
    assert result.value == 1 and result.explanation == "Matches."
    assert all(text in prompts[0] for text in ("What color?", "Blue.", "Ref: blue."))

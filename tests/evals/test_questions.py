"""Offline checks on the question files. No API calls, no Inspect."""

import pytest

from tests.evals.questions import load_questions, prompt_for

CODEGEN = load_questions("codegen")


def test_question_ids_are_unique():
    ids = [q["id"] for q in load_questions("codegen") + load_questions("skill_selection")]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("question", CODEGEN, ids=[q["id"] for q in CODEGEN])
def test_codegen_question_is_well_formed(question):
    assert question["requires_data"]
    assert question["expected"]
    assert all(isinstance(v, (int, float)) for v in question["expected"].values())
    prompt = prompt_for(question)  # raises KeyError on an unknown packet
    assert all(f'"{key}"' in prompt for key in question["expected"])

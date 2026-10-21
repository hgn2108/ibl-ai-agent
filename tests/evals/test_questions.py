"""Offline checks on the question files. No API calls, no Inspect."""

import pytest

from tests.evals.questions import load_questions, named_skills, prompt_for, skill_descriptions

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


SKILL_QUESTIONS = load_questions("skill_selection")


@pytest.mark.parametrize("question", SKILL_QUESTIONS, ids=[q["id"] for q in SKILL_QUESTIONS])
def test_expected_skills_exist(question):
    # A renamed skill would make the question unpassable.
    assert set(question["expected_skills"]) <= {
        line.split(":")[0].removeprefix("- ") for line in skill_descriptions().splitlines()
    }


def test_named_skills_reads_the_list_after_the_last_skills_line():
    reply = "Skills: none yet.\nibl-report is out.\n\n**Skills**:\n- ibl-load\n* `ibl-anatomy`\n\nibl-analyze\n"
    assert named_skills(reply) == {"ibl-load", "ibl-anatomy", "ibl-analyze"}


def test_a_reply_without_a_skills_line_names_nothing():
    assert named_skills("ibl-load\nibl-anatomy") == set()

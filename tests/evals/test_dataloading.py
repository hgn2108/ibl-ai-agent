"""Data-loading evals across three provider architectures.

Runs every question in `questions/` against every model in the grid, using the
actor hierarchy in `actors/` and deepeval for test cases, metrics and pass/fail.

    UV_CACHE_DIR=.uv-cache uv run --no-sync pytest tests/evals/test_dataloading.py -n 4

The grid comes from conftest (`models.json`, else `models.default.json`). To use
the committed multi-provider grid:

    cp tests/evals/models.grid.json tests/evals/models.json

Why actors rather than deepeval's own model classes: `DeepEvalBaseLLM.generate`
returns a string, with nowhere to carry token usage (which we must report) and
no way to express an agent session or a tool loop. Claude runs as a local Claude
Code agent via claude-agent-sdk; Mistral and Lightning are chat endpoints given
a single `run_python` tool so they can also compute answers from the local data.
Deepeval sits above that, judging the answers.

Usage per run is written to `results/usage.csv` and summarised in the terminal.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from deepeval.test_case import LLMTestCase

from tests.evals.actors import build_actor
from tests.evals.metrics import build_metrics
from tests.evals.skill_router import get_skill_files
from tests.evals.test_codegen import assert_test

_DIR = Path(__file__).parent
REPO_ROOT = _DIR.parents[1]
RESULTS_DIR = _DIR / "results"
USAGE_CSV = RESULTS_DIR / "usage.csv"


def load_questions():
    """Every question in questions/, tagged with the file it came from."""
    questions = []
    for path in sorted((_DIR / "questions").glob("*.json")):
        for question in json.loads(path.read_text()):
            questions.append({**question, "source": path.stem})
    return questions


QUESTIONS = load_questions()


def context_for(question):
    """Reference material for a question, from the skill files it declares.

    Each question names `packets` (the Required Load Packets of AGENTS.md).
    Without them a model has to guess repo conventions -- which region mapping,
    what counts as a good unit -- so the eval would measure guesswork rather
    than data loading. test_codegen.py supplies the same context.
    """
    if not question.get("packets"):
        return ""
    files = get_skill_files(*question["packets"])
    return "\n\n".join(f"--- {path.name} ---\n{path.read_text()}" for path in files)


def prompt_for(question):
    """The prompt sent to a model: reference material, question, how to answer.

    Output format is specified so that a failure reflects the data work rather
    than a guess at what shape we wanted.
    """
    context = context_for(question)
    preamble = (
        f"Use the following reference materials to answer the question.\n\n{context}\n\n"
        if context
        else ""
    )
    return (
        f"{preamble}Question: {question['question']}\n\n"
        "Compute the answer from the local IBL datasets by writing and running "
        "Python with the run_python tool. Report every number you are asked for "
        "explicitly in your final message."
    )


def record_usage(model_name, question_id, usage, passed):
    """Append one run's usage to results/usage.csv.

    Appending per run (rather than writing at the end) means an interrupted
    grid still leaves the completed rows behind.
    """
    RESULTS_DIR.mkdir(exist_ok=True)
    is_new = not USAGE_CSV.exists()
    with USAGE_CSV.open("a", newline="") as handle:
        writer = csv.writer(handle)
        if is_new:
            writer.writerow(
                ["model", "question", "passed", "input_tokens", "output_tokens",
                 "cache_read_tokens", "cache_write_tokens", "cost_usd", "num_turns",
                 "stop_reason"]
            )
        writer.writerow(
            [model_name, question_id, passed, usage.input_tokens, usage.output_tokens,
             usage.cache_read_tokens, usage.cache_write_tokens, round(usage.cost_usd, 6),
             usage.num_turns, usage.stop_reason]
        )


@pytest.mark.parametrize("question", QUESTIONS, ids=[q["id"] for q in QUESTIONS])
def test_question(model_cfg, question):
    """One question against one model, graded by the question's own metrics.

    `model_cfg` is parametrized by conftest over the whole grid, so pytest
    expands this into the full model x question matrix.
    """
    if question.get("task") == "skill_selection":
        pytest.skip("skill selection is tested in test_skill_selection.py")

    actor = build_actor(model_cfg, cwd=REPO_ROOT)
    result = actor.run(prompt_for(question))

    test_case = LLMTestCase(input=question["question"], actual_output=result.reply)
    metrics = build_metrics(question["checks"])

    passed = True
    try:
        assert_test(test_case, metrics)
    except AssertionError:
        passed = False
        raise
    finally:
        record_usage(actor.name, question["id"], result.usage, passed)

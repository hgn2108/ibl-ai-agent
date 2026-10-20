"""Inspect tasks. Run one or more models against every question:

    inspect eval tests/evals/tasks.py --model anthropic/claude-haiku-4-5,mistral/mistral-small-latest

Keys go in ``.env`` (see ``tests/evals/.env.template``). Model-written code runs in the
Docker sandbox of ``sandbox/compose.yaml``: no network, read-only repo. The data
questions need ``bwm_ephys`` (``scripts/download_datasets.py``) under the repo.
"""

import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import Score, accuracy, scorer, stderr
from inspect_ai.solver import generate, use_tools
from inspect_ai.tool import python

from tests.evals.checks import mismatches
from tests.evals.questions import load_questions, named_skills, prompt_for, skill_prompt_for

SANDBOX = ("docker", str(Path(__file__).parent.joinpath("sandbox", "compose.yaml")))


@scorer(metrics=[accuracy(), stderr()])
def exact_answer():
    """Pass when the reply's final JSON object equals the question's ``expected``."""

    async def score(state, target):
        wrong = mismatches(state.output.completion, json.loads(target.text))
        return Score(value=int(not wrong), explanation=f"(got, expected) per key: {wrong}")

    return score


@task
def dataloading():
    """Data-loading questions: the model runs Python in the sandbox and answers in JSON."""
    samples = [
        Sample(id=q["id"], input=prompt_for(q), target=json.dumps(q["expected"]))
        for q in load_questions("codegen")
    ]
    return Task(
        dataset=samples,
        solver=[use_tools(python(timeout=180)), generate()],
        scorer=exact_answer(),
        sandbox=SANDBOX,
        message_limit=30,
    )


@scorer(metrics=[accuracy(), stderr()])
def names_expected_skills():
    """Pass when the reply names every skill in the question's ``expected_skills``."""

    async def score(state, target):
        missing = set(json.loads(target.text)) - named_skills(state.output.completion)
        return Score(value=int(not missing), explanation=f"skills not named: {sorted(missing)}")

    return score


@task
def skill_selection():
    """Does the model pick the skills a question needs? Reading only: no tools, no sandbox."""
    samples = [
        Sample(id=q["id"], input=skill_prompt_for(q), target=json.dumps(q["expected_skills"]))
        for q in load_questions("skill_selection")
    ]
    return Task(dataset=samples, solver=generate(), scorer=names_expected_skills())

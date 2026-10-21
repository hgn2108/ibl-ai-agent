"""Private scientific benchmark as an Inspect task.

Questions live outside the repository, in a JSON list of ``{id, category, question}``:

    SCIENTIFIC_BENCHMARK_QUESTIONS=/private/questions.json \\
        inspect eval tests/evals/scientific_benchmark.py --model <id> --log-dir /private/logs

Inspect logs hold runtime, tokens, cost and status. The judge scorer is injected by
the caller, so rubrics and reference answers stay private too.
"""

import json
import os
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import generate

REQUIRED = ("id", "category", "question")


def load_benchmark(path: str | Path) -> list[Sample]:
    """Validate a private question file and return its samples; no model calls.

    Parameters
    ----------
    path
        JSON file holding a list of objects with ``id``, ``category`` and ``question``.

    Returns
    -------
    list[Sample]
        One sample per question, with the category as metadata.

    Raises
    ------
    ValueError
        If the file is not a list, a field is missing or empty, or an id repeats.
    """
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list) or not rows:
        raise ValueError("question file must be a non-empty JSON list")
    for row in rows:
        missing = [k for k in REQUIRED if not str(row.get(k, "")).strip()]
        if missing:
            raise ValueError(f"question {row.get('id')!r} lacks {missing}")
    ids = [row["id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("question ids must be unique")
    return [
        Sample(id=r["id"], input=r["question"], metadata={"category": r["category"]}) for r in rows
    ]


@task
def scientific_benchmark(scorer, questions: str | None = None):
    """Ask each private question and grade the reply with the injected ``scorer``.

    Parameters
    ----------
    scorer
        An Inspect scorer, e.g. one wrapping the private judge.
    questions
        Path of the question file; defaults to ``$SCIENTIFIC_BENCHMARK_QUESTIONS``.
    """
    path = questions or os.environ["SCIENTIFIC_BENCHMARK_QUESTIONS"]
    return Task(dataset=load_benchmark(path), solver=generate(), scorer=scorer)

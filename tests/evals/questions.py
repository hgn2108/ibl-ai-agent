"""Question files and the prompts built from them. Stdlib only, so offline tests can use it."""

from __future__ import annotations

import json
import re
from pathlib import Path

from tests.evals.checks import answer_instructions
from tests.evals.skill_router import get_skill_files

_DIR = Path(__file__).parent
REPO_ROOT = _DIR.parents[1]


def load_questions(task: str) -> list[dict]:
    """Return every question of one ``task`` type from ``questions/*.json``."""
    questions = []
    for path in sorted(_DIR.joinpath("questions").glob("*.json")):
        questions += [q for q in json.loads(path.read_text()) if q.get("task") == task]
    return questions


def prompt_for(question: dict) -> str:
    """Build a data-loading prompt: reference material, the question, how to answer.

    Each question names ``packets`` (the Required Load Packets of AGENTS.md).
    Without them a model must guess repo conventions, such as which region
    mapping or what counts as a good unit, so the eval would measure guesswork
    rather than data loading. The answer format is fixed so that a failure
    reflects the data work, not a guess at what shape we wanted.

    Parameters
    ----------
    question : dict
        A question entry with ``question``, ``expected`` and optional ``packets``.

    Returns
    -------
    str
    """
    files = get_skill_files(*question.get("packets", []))
    context = "\n\n".join(f"--- {path.name} ---\n{path.read_text()}" for path in files)
    preamble = f"Use the following reference materials.\n\n{context}\n\n" if context else ""
    return (
        f"{preamble}Question: {question['question']}\n\n"
        "Compute the answer from the local IBL datasets by running Python. Every Python "
        "call is a fresh process, so variables and imports do not persist: write each call "
        "as a complete script. "
        f"{answer_instructions(question['expected'])}"
    )


def skill_descriptions() -> str:
    """Return one ``- <skill>: <description>`` line per skill in ``skills/``.

    Only repo skills are listed, never ``~/.claude/skills``: the eval must not
    depend on what happens to be installed on the machine running it.
    """
    lines = []
    for skill_md in sorted(REPO_ROOT.joinpath("skills").glob("*/SKILL.md")):
        for line in skill_md.read_text(encoding="utf-8").splitlines():
            if line.startswith("description:"):
                lines.append(f"- {skill_md.parent.name}: {line.removeprefix('description:')}")
                break
    return "\n".join(lines)


def skill_prompt_for(question: dict) -> str:
    """Build the skill-selection prompt: AGENTS.md, the skill list, the question."""
    return (
        f"{REPO_ROOT.joinpath('AGENTS.md').read_text(encoding='utf-8')}\n\n"
        f"Available skills:\n{skill_descriptions()}\n\n"
        f"Question: {question['question']}\n\n"
        "Think briefly about which skills this question needs. Then end your reply with a "
        "line `Skills:` followed by the needed skill names, exactly as written in the list "
        "above (not file paths), one per line."
    )


_SKILLS_LINE = re.compile(r"(?im)^\W*skills\W*:\W*$")


def named_skills(reply: str) -> set[str]:
    """Return the skill names listed after the last ``Skills:`` line of a reply.

    One name per line; list markers and backticks are ignored. A reply without a
    ``Skills:`` line names nothing: following the answer format is part of the task.
    """
    tail = _SKILLS_LINE.split(reply)[-1] if _SKILLS_LINE.search(reply) else ""
    return {line.strip().lstrip("-* ").strip("`") for line in tail.splitlines()} - {""}

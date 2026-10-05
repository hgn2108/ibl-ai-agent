"""Grade a model's answer to a behaviour eval question against ground truth.

Grading is deliberately mechanical: the model is asked to end its reply with a
```json block holding the keys in the question's answer_schema, and we compare
those values to `ground_truth.json`. No LLM judges the answer, so a pass means
the number matched, not that a grader found the prose convincing.

Counts must match exactly (tolerance 0). Proportions are compared with a
tolerance, because a model may legitimately round.
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).parent
GROUND_TRUTH = json.loads((HERE / "ground_truth.json").read_text())
QUESTIONS = json.loads((HERE / "questions.json").read_text())


def extract_answer(reply):
    """Return the dict from the last ```json block in a model reply, or None.

    The last block is used rather than the first: models often show a worked
    example or intermediate output before their final answer.
    """
    blocks = re.findall(r"```json\s*(.*?)\s*```", reply, re.DOTALL)
    if not blocks:
        return None
    return json.loads(blocks[-1])


def values_match(expected, actual, tolerance):
    """Compare a ground-truth value to a model's value, recursing into dicts.

    Dict keys are compared as strings, so {'0.2': 0.62} and {0.2: 0.62} both
    pass -- JSON has no numeric keys, and that is a formatting artefact rather
    than a wrong answer.

    A key missing on either side counts as 0. An empty category (rightCamera has
    no DeepLabCut sessions) is reported either as "dlc": 0 or by leaving the key
    out, and both describe the same data. Omitting a non-zero key still fails,
    because 0 will not match the expected count.
    """
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        actual = {str(k): v for k, v in actual.items()}
        expected = {str(k): v for k, v in expected.items()}
        return all(
            values_match(expected.get(key, 0), actual.get(key, 0), tolerance)
            for key in set(expected) | set(actual)
        )
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(expected - actual) <= tolerance
    return expected == actual


def grade(question, reply):
    """Grade one reply. Returns (passed, detail dict of per-check results).

    A reply with no parsable json block fails every check -- an answer we
    cannot read is not an answer.
    """
    truth = GROUND_TRUTH[question["ground_truth_key"]]
    try:
        answer = extract_answer(reply)
    except json.JSONDecodeError:
        answer = None

    results = {}
    for check in question["checks"]:
        key, tolerance = check["path"], check["tolerance"]
        expected = truth[key]
        actual = None if answer is None else answer.get(key)
        results[key] = {
            "expected": expected,
            "actual": actual,
            "passed": actual is not None and values_match(expected, actual, tolerance),
        }
    return all(r["passed"] for r in results.values()), results


def prompt_for(question):
    """Return the full prompt sent to a model: the question plus answer format.

    The required output format is part of the prompt so that failures reflect
    the data work rather than a model guessing what shape we wanted.
    """
    schema = json.dumps(question["answer_schema"], indent=2)
    return (
        f"{question['question']}\n\n"
        "Work it out from the local dataset by writing and running Python. "
        "End your reply with a ```json block containing exactly these keys:\n"
        f"{schema}"
    )

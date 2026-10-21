"""Grade a model reply against a question's ``expected`` answer.

A question lists its answer as a flat dict, e.g. ``{"CB_good": 7273}``. The prompt
asks the model to end with a JSON object with those keys, so grading is a dict
comparison: no metric class, and a new question needs no code.
"""

from __future__ import annotations

import json


def answer_instructions(expected: dict) -> str:
    """Return the prompt sentence that fixes the answer format."""
    keys = ", ".join(f'"{key}"' for key in expected)
    return (
        f"End your reply with one JSON object with exactly the keys {keys}, "
        "and plain numbers (no strings, no thousands separators) as values."
    )


def last_json_object(text: str) -> dict | None:
    """Return the last top-level JSON object in ``text``, or None."""
    decoder, found, pos = json.JSONDecoder(), None, text.find("{")
    while pos != -1:
        try:
            obj, end = decoder.raw_decode(text, pos)
        except ValueError:
            pos = text.find("{", pos + 1)
            continue
        found = obj if isinstance(obj, dict) else found
        pos = text.find("{", end)
    return found


def mismatches(reply: str, expected: dict) -> dict:
    """Return ``{key: (got, expected)}`` for every wrong or missing value.

    Empty means the reply is correct. ``got`` is None when the key, or the whole
    JSON answer, is missing.
    """
    answer = last_json_object(reply) or {}
    return {k: (answer.get(k), v) for k, v in expected.items() if answer.get(k) != v}

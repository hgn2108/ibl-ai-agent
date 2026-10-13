"""Unit tests for answer grading. No API calls."""

import pytest

from tests.evals.checks import last_json_object, mismatches

EXPECTED = {"left": 1783, "right": 235}


def test_correct_answer_has_no_mismatches():
    assert not mismatches('Counted.\n{"left": 1783, "right": 235}', EXPECTED)


def test_swapped_values_are_caught():
    # Matching numbers anywhere in the text would pass this.
    assert mismatches('{"left": 235, "right": 1783}', EXPECTED).keys() == {"left", "right"}


@pytest.mark.parametrize("reply", ["1783 and 235", '{"left": 1783}', '{"left": "1783", "right": 235}'])
def test_missing_or_mistyped_values_fail(reply):
    assert mismatches(reply, EXPECTED)


def test_last_object_wins_and_nested_objects_are_not_split():
    reply = 'draft {"left": 1} final {"outer": {"inner": 2}}'
    assert last_json_object(reply) == {"outer": {"inner": 2}}

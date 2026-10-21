"""Baseline scorer construction. Grading itself is Inspect's and needs a live model."""

import pytest

pytest.importorskip("inspect_ai")

from tests.evals.scientific_baseline import GENERAL_CRITERIA, scientific_baseline  # noqa: E402


def test_default_and_custom_criteria_build_a_scorer():
    assert callable(scientific_baseline())
    assert callable(scientific_baseline("Custom criteria."))
    assert GENERAL_CRITERIA.strip()


def test_empty_criteria_are_rejected():
    with pytest.raises(ValueError, match="criteria"):
        scientific_baseline(" ")

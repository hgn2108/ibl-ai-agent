"""Scientific-reasoning scorer with a mocked judge. No API calls."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

pytest.importorskip("inspect_ai")

from tests.evals.scientific_reasoning import scientific_reasoning  # noqa: E402


def _judgment(score, claims=()):
    return SimpleNamespace(normalized_score=score, reason="why", unsupported_claims=list(claims))


def _score(judge, **kwargs):
    state = SimpleNamespace(input_text="Q", output=SimpleNamespace(completion="A"))
    return asyncio.run(scientific_reasoning(judge, "E", **kwargs)(state, None))


def test_judge_receives_question_answer_and_evidence():
    judge = AsyncMock(return_value=_judgment(1.0))
    result = _score(judge)
    judge.assert_awaited_once_with(question="Q", answer="A", evidence="E")
    assert result.value == 1


def test_low_score_fails_and_lists_unsupported_claims():
    result = _score(AsyncMock(return_value=_judgment(0.5, ["bad claim"])))
    assert result.value == 0
    assert "bad claim" in result.explanation
    assert result.metadata["normalized_score"] == 0.5


def test_threshold_is_configurable_and_validated():
    assert _score(AsyncMock(return_value=_judgment(0.5)), threshold=0.5).value == 1
    with pytest.raises(ValueError, match="between 0 and 1"):
        scientific_reasoning(Mock(), "E", threshold=2)

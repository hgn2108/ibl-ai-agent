"""Offline tests for the reusable custom LLM judge."""

import json
import subprocess

import pytest

from tests.evals import custom_llm_judge
from tests.evals.custom_llm_judge import (
    claude_cli_generate,
    judge_answer,
    parse_judgment,
)


def prompt_builder(question, answer, evidence):
    """Build a harmless test prompt."""
    return f"{question}|{answer}|{evidence}"


def response(score=2):
    """Return a mocked JSON judge response."""
    return json.dumps(
        {
            "score": score,
            "reason": "Mock evaluation",
            "unsupported_claims": [],
        }
    )


@pytest.mark.parametrize("score", [0, 1, 2])
def test_valid_scores(score):
    result = parse_judgment(response(score))
    assert result.score == score
    assert result.normalized_score == score / 2


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        '{"score": 3, "reason": "Invalid", "unsupported_claims": []}',
        '{"score": true, "reason": "Invalid", "unsupported_claims": []}',
        '{"score": 2, "reason": "", "unsupported_claims": []}',
        '{"score": 2, "reason": "OK", "unsupported_claims": [42]}',
    ],
)
def test_invalid_responses(raw):
    with pytest.raises(ValueError):
        parse_judgment(raw)


def test_question_answer_evidence_forwarded():
    prompts = []

    def generate(prompt):
        prompts.append(prompt)
        return response()

    result = judge_answer("Question", "Answer", "Evidence", prompt_builder, generate)

    assert prompts == ["Question|Answer|Evidence"]
    assert result.normalized_score == 1.0


def test_empty_evidence_rejected():
    with pytest.raises(ValueError, match="Evidence"):
        judge_answer("Q", "A", "", prompt_builder, lambda _: response())


def test_retry_after_invalid_json():
    responses = iter(["invalid", response(1)])

    result = judge_answer(
        "Q",
        "A",
        "E",
        prompt_builder,
        lambda _: next(responses),
    )

    assert result.score == 1


def test_repeated_invalid_json_raises():
    calls = []

    def generate(prompt):
        calls.append(prompt)
        return "invalid"

    with pytest.raises(ValueError, match="2 attempts"):
        judge_answer("Q", "A", "E", prompt_builder, generate)

    assert len(calls) == 2


def test_valid_response_does_not_retry():
    calls = []

    def generate(prompt):
        calls.append(prompt)
        return response(2)

    judge_answer("Q", "A", "E", prompt_builder, generate)

    assert len(calls) == 1


def test_backend_error_propagates():
    def generate(prompt):
        raise RuntimeError("Backend unavailable")

    with pytest.raises(RuntimeError, match="Backend unavailable"):
        judge_answer("Q", "A", "E", prompt_builder, generate)


def test_claude_cli_disables_tools(monkeypatch):
    """Verify CLI arguments without calling Claude."""
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=response(),
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert claude_cli_generate("Test prompt") == response()
    assert calls[0][0][-2:] == ["--tools", ""]
    assert calls[0][1]["timeout"] == 120


def test_custom_claude_model(monkeypatch):
    """Verify that the selected Claude model is forwarded."""
    calls = []

    def fake_claude(prompt, model="sonnet", timeout=120):
        calls.append((prompt, model))
        return response()

    monkeypatch.setattr(
        custom_llm_judge,
        "claude_cli_generate",
        fake_claude,
    )

    result = judge_answer(
        "Q",
        "A",
        "E",
        prompt_builder,
        model="opus",
    )

    assert result.score == 2
    assert calls == [("Q|A|E", "opus")]


@pytest.mark.parametrize("model", ["sonnet", "opus", "haiku"])
def test_supported_claude_models(monkeypatch, model):
    """Verify model selection without making live calls."""
    selected_models = []

    def fake_claude(prompt, model="sonnet", timeout=120):
        selected_models.append(model)
        return response()

    monkeypatch.setattr(
        custom_llm_judge,
        "claude_cli_generate",
        fake_claude,
    )

    judge_answer(
        "Q",
        "A",
        "E",
        prompt_builder,
        model=model,
    )

    assert selected_models == [model]


def test_custom_generator_takes_precedence(monkeypatch):
    """Verify that an injected generator overrides Claude CLI."""

    def unexpected_claude(*args, **kwargs):
        raise AssertionError("Claude CLI should not be called")

    monkeypatch.setattr(
        custom_llm_judge,
        "claude_cli_generate",
        unexpected_claude,
    )

    result = judge_answer(
        "Q",
        "A",
        "E",
        prompt_builder,
        generate=lambda _: response(1),
        model="opus",
    )

    assert result.score == 1

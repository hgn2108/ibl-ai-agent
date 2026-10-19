"""Offline tests for the Claude CLI DeepEval adapter."""

from unittest.mock import patch

from pydantic import BaseModel

from tests.evals.claude_cli_model import ClaudeCLIModel


def test_model_name():
    """Check the model identifier."""
    model = ClaudeCLIModel("sonnet")
    assert model.get_model_name() == "claude-cli-sonnet"


def test_generate():
    """Check that generation uses the existing CLI function."""
    with patch(
        "tests.evals.claude_cli_model.claude_cli_generate",
        return_value="Test response",
    ) as generate:
        result = ClaudeCLIModel("sonnet").generate("Test prompt")

    assert result == "Test response"
    generate.assert_called_once_with("Test prompt", model="sonnet")


class ScoreResponse(BaseModel):
    score: int
    reason: str


def test_structured_generation():
    """Parse a structured Claude response into a Pydantic model."""
    with patch(
        "tests.evals.claude_cli_model.claude_cli_generate",
        return_value='{"score": 2, "reason": "Supported by evidence"}',
    ) as generate:
        result = ClaudeCLIModel().generate("Evaluate", schema=ScoreResponse)

    assert result.score == 2
    assert result.reason == "Supported by evidence"
    assert "Return only a valid JSON object" in generate.call_args.args[0]

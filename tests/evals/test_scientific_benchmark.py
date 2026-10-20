import pytest
import json

from tests.evals.actors import RunResult, Usage
from tests.evals.scientific_benchmark import load_questions, run_question


def test_load_questions(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text(json.dumps([{"id": "Q01", "question": "Example"}]))
    assert load_questions(path)[0]["id"] == "Q01"


def test_token_usage():
    class FakeActor:
        name = "mock-model"

        def run(self, prompt):
            return RunResult("Example answer", Usage(input_tokens=100, output_tokens=50))

    row = run_question(FakeActor(), {"id": "Q01", "question": "Example"})
    assert row["status"] == "completed"
    assert row["input_tokens"] == 100
    assert row["output_tokens"] == 50
    assert row["scientific_score"] == ""


def test_duplicate_ids(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text(json.dumps([
        {"id": "Q01", "question": "First"},
        {"id": "Q01", "question": "Second"},
    ]))
    with pytest.raises(ValueError, match="Duplicate"):
        load_questions(path)


def test_incomplete_response():
    class FakeActor:
        name = "mock-model"

        def run(self, prompt):
            return RunResult("", Usage(stop_reason="max_tokens"))

    row = run_question(FakeActor(), {"id": "Q01", "question": "Private"})
    assert row["status"] == "incomplete"


def test_error_does_not_leak_question():
    class FakeActor:
        name = "mock-model"

        def run(self, prompt):
            raise RuntimeError("Private question and answer")

    row = run_question(FakeActor(), {"id": "Q01", "question": "Private"})
    assert row["status"] == "error"
    assert "Private question" not in str(row)


def test_csv_excludes_private_text(tmp_path):
    from tests.evals.scientific_benchmark import append_result

    class FakeActor:
        name = "mock-model"

        def run(self, prompt):
            return RunResult("SECRET ANSWER", Usage())

    row = run_question(
        FakeActor(),
        {"id": "Q01", "question": "SECRET QUESTION"},
    )
    path = tmp_path / "results.csv"
    append_result(path, row)
    contents = path.read_text()
    assert "SECRET QUESTION" not in contents
    assert "SECRET ANSWER" not in contents

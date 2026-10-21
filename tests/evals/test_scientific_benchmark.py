"""Private-question validation. No API calls."""

import json

import pytest

pytest.importorskip("inspect_ai")

from tests.evals.scientific_benchmark import load_benchmark  # noqa: E402

ROW = {"id": "a", "category": "c", "question": "Q?"}


def _write(tmp_path, rows):
    path = tmp_path.joinpath("q.json")
    path.write_text(json.dumps(rows))
    return path


def test_valid_file_gives_samples_with_category(tmp_path):
    (sample,) = load_benchmark(_write(tmp_path, [ROW]))
    assert (sample.id, sample.input, sample.metadata) == ("a", "Q?", {"category": "c"})


@pytest.mark.parametrize(
    "rows",
    [[], {"id": "a"}, [{**ROW, "question": " "}], [{"id": "a", "question": "Q"}], [ROW, ROW]],
)
def test_invalid_files_are_rejected(tmp_path, rows):
    with pytest.raises(ValueError):
        load_benchmark(_write(tmp_path, rows))

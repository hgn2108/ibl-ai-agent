"""The log summary, from a real Inspect run with a scripted model. No API calls, no Docker."""

import pytest

pytest.importorskip("inspect_ai")

from inspect_ai import eval as inspect_eval  # noqa: E402
from inspect_ai.model import ModelOutput, get_model  # noqa: E402

from tests.evals.summarize import summarize  # noqa: E402
from tests.evals.tasks import skill_selection  # noqa: E402


@pytest.mark.parametrize("reply, outcome", [("Skills:\n- ibl-load\n- ibl-anatomy", "pass"), ("Skills:\nibl-load", "fail")])
def test_skill_selection_run_is_scored_and_summarized(tmp_path, reply, outcome):
    model = get_model("mockllm/model", custom_outputs=[ModelOutput.from_content("mockllm/model", reply)])
    inspect_eval(skill_selection(), model=model, log_dir=str(tmp_path), display="none")
    table = summarize(tmp_path)
    assert "mockllm/model" in table and outcome in table

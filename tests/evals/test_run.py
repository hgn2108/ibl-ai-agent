"""Model-list loading for ``run.py``. No API calls, no Inspect."""

import json

from tests.evals.run import HERE, load_models


def test_the_committed_default_is_a_nonempty_list_of_provider_slash_model_ids():
    models = load_models()
    assert models and all("/" in m for m in models)
    assert HERE.joinpath("models.json").exists()


def test_models_argument_overrides_the_file(tmp_path):
    file = tmp_path.joinpath("m.json")
    file.write_text(json.dumps(["file/model"]))
    assert load_models("a/x, b/y,", file) == ["a/x", "b/y"]
    assert load_models("  ", file) == ["file/model"]

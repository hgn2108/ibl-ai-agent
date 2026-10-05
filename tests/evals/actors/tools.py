"""The one tool chat-only actors get: run Python in the repo environment.

Claude's SDK brings its own tools. Lightning and Mistral are plain chat
endpoints, so to answer a data-loading question they need some way to execute
code. This module provides the minimum: a single `run_python` function, its
JSON schema for function calling, and a subprocess runner.

This executes model-written code on the machine running the evals, with no
sandbox. That is inherent to the task -- the question is "load this dataset and
compute a number" -- but it means evals should be run on a machine where that
is acceptable, and never against an untrusted question set.
"""

from __future__ import annotations

import subprocess

TIMEOUT_S = 180
MAX_OUTPUT_CHARS = 10_000

# Function-calling schema, in the shape both OpenAI-compatible and Mistral APIs
# expect. The description tells the model how to reach the datasets, since it
# cannot explore the repo the way an agent with file tools would.
RUN_PYTHON_TOOL = {
    "type": "function",
    "function": {
        "name": "run_python",
        "description": (
            "Execute Python in the ibl-ai-agent repo environment and return stdout "
            "and stderr. pandas is available. Resolve dataset directories with: "
            "from ibl_ai_agent.data_locations import resolve_dataset_dir; "
            "root = resolve_dataset_dir('bwm_behavior'). Tables are parquet files "
            "under root, e.g. metadata/trials.parquet. Print what you want to see."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python source to execute."}
            },
            "required": ["code"],
        },
    },
}


def run_python(code, cwd):
    """Run `code` with the repo's interpreter and return combined output as text.

    Output is truncated to MAX_OUTPUT_CHARS so one careless print of a whole
    dataframe cannot blow up the context. A timeout or crash is returned as
    text, not raised: the model should see its own error and get a chance to
    fix it, which is what the turn limit is for.
    """
    completed = subprocess.run(
        [".venv/bin/python", "-c", code],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
        env={"UV_CACHE_DIR": ".uv-cache", "PATH": "/usr/bin:/bin", "HOME": str(cwd)},
    )
    output = (completed.stdout + completed.stderr).strip() or "(no output)"
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n...[truncated]"
    return output

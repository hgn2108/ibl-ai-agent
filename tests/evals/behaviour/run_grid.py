"""Run the behaviour eval grid: every question against every model, N times.

    UV_CACHE_DIR=.uv-cache uv run --no-sync python tests/evals/behaviour/run_grid.py --repeats 3

Writes three files to results/:
  runs.csv      one row per (model, question, repeat) with pass/fail and tokens
  results.json  the same runs plus each model's full reply, for inspecting failures
  grid.md       the pass-rate grid and token table to put on a slide

Repeats matter: a single run cannot separate a model that is reliable from one
that got lucky, and these questions are answered by generated code, which varies
between runs.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from grader import QUESTIONS, grade, prompt_for  # noqa: E402

from tests.evals.actors import build_actor  # noqa: E402

HERE = Path(__file__).parent
REPO_ROOT = HERE.parents[2]
RESULTS_DIR = HERE / "results"

# The 3 x 3 grid. Provider is per-model, so a future row can point at a
# different API without touching anything else.
MODELS = [
    {"name": "opus-5", "provider": "claude", "model": "opus"},
    {"name": "sonnet-5", "provider": "claude", "model": "sonnet"},
    {"name": "haiku-4.5", "provider": "claude", "model": "haiku"},
]


def run_one(question, model_cfg):
    """Run one question once against one model. Returns a flat result dict."""
    started = time.time()
    actor = build_actor(model_cfg, cwd=REPO_ROOT)
    result = actor.run(prompt_for(question))
    passed, detail = grade(question, result.reply)
    return {
        "model": actor.name,
        "question": question["id"],
        "passed": passed,
        "seconds": round(time.time() - started, 1),
        **result.usage.as_dict(),
        "checks": detail,
        "reply": result.reply,
    }


def build_grid(runs):
    """Return (pass-rate grid as %, per-model token/cost summary) as DataFrames."""
    df = pd.DataFrame(runs)
    grid = df.pivot_table(index="model", columns="question", values="passed", aggfunc="mean") * 100
    grid["overall %"] = df.groupby("model").passed.mean() * 100
    tokens = df.groupby("model").agg(
        input_tokens=("input_tokens", "sum"),
        output_tokens=("output_tokens", "sum"),
        cache_read_tokens=("cache_read_tokens", "sum"),
        cost_usd=("cost_usd", "sum"),
        median_seconds=("seconds", "median"),
    )
    return grid.round(0), tokens.round({"cost_usd": 4, "median_seconds": 1})


def main(repeats, only_model, only_question):
    """Run the grid. Re-running a subset keeps the other questions' stored runs,
    so a single question can be revised without paying to re-run the rest."""
    models = [m for m in MODELS if only_model in (None, m["name"])]
    questions = [q for q in QUESTIONS if only_question in (None, q["id"])]
    previous = RESULTS_DIR / "results.json"
    kept = [
        r for r in json.loads(previous.read_text())
        if previous.exists() and r["question"] not in {q["id"] for q in questions}
    ] if previous.exists() else []
    runs = []
    for model_cfg in models:
        for question in questions:
            for repeat in range(repeats):
                run = run_one(question, model_cfg)
                run["repeat"] = repeat
                runs.append(run)
                mark = "PASS" if run["passed"] else "FAIL"
                print(
                    f"{model_cfg['name']:10s} {question['id']:34s} r{repeat} "
                    f"{mark} {run['seconds']:6.1f}s  ${run['cost_usd']:.4f}"
                )

    runs = kept + runs
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "results.json").write_text(json.dumps(runs, indent=2))
    columns = ["model", "question", "repeat", "passed", "seconds", "input_tokens",
               "output_tokens", "cache_read_tokens", "cost_usd", "num_turns"]
    pd.DataFrame(runs)[columns].to_csv(RESULTS_DIR / "runs.csv", index=False)

    grid, tokens = build_grid(runs)
    report = (
        f"# Behaviour eval grid\n\n{repeats} repeat(s) per cell, "
        f"{len(MODELS)} models x {len(QUESTIONS)} questions\n\n"
        f"## Pass rate (%)\n\n{grid.to_markdown()}\n\n"
        f"## Token usage and cost (summed over all runs)\n\n{tokens.to_markdown()}\n"
    )
    (RESULTS_DIR / "grid.md").write_text(report)
    print("\n" + report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3, help="runs per model/question cell")
    parser.add_argument("--model", default=None, help="run a single model by name")
    parser.add_argument("--question", default=None, help="run a single question by id")
    args = parser.parse_args()
    main(args.repeats, args.model, args.question)

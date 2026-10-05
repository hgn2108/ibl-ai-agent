"""Turn results/usage.csv into the summary table.

    UV_CACHE_DIR=.uv-cache uv run --no-sync python tests/evals/summarize_results.py

Writes results/summary.md and prints it. One row per model: pass rate, how each
run ended, tokens and cost.

`stop_reason` is reported because three failures that score the same are not the
same result: a model that ran out of turns was still trying, one that stopped
early returned a confident wrong answer, and one that never answered hit a
provider error. Only the first two say anything about the model's data skills.
"""

import sys
from pathlib import Path

import pandas as pd

RESULTS_DIR = Path(__file__).parent / "results"
USAGE_CSV = RESULTS_DIR / "usage.csv"
SUMMARY_MD = RESULTS_DIR / "summary.md"

# Cost is only reported by the Claude CLI; Mistral and Lightning return none.
NO_COST = "not reported"


def summarize(runs):
    """One row per model: pass rate, stop reasons, tokens, cost.

    Input tokens include cache reads, which dominate for agent runs that re-read
    context every turn.
    """
    runs = runs.assign(input_total=runs.input_tokens + runs.cache_read_tokens)
    summary = runs.groupby("model").agg(
        runs_=("passed", "size"),
        passed=("passed", "sum"),
        stop_reasons=("stop_reason", lambda s: ", ".join(sorted(set(s)))),
        turns=("num_turns", "median"),
        input_tokens=("input_total", "sum"),
        output_tokens=("output_tokens", "sum"),
        cost_usd=("cost_usd", "sum"),
    )
    summary["pass_rate"] = (100 * summary.passed / summary.runs_).round(0).astype(int)
    summary["cost"] = summary.cost_usd.map(lambda c: f"${c:.2f}" if c else NO_COST)
    return summary.sort_values(["pass_rate", "model"], ascending=[False, True])


def to_markdown(summary, runs):
    """Render the summary as markdown, with a one-line header of totals."""
    table = summary[
        ["pass_rate", "stop_reasons", "turns", "input_tokens", "output_tokens", "cost"]
    ].rename(
        columns={
            "pass_rate": "pass %",
            "stop_reasons": "how runs ended",
            "turns": "median turns",
            "input_tokens": "input tokens (incl. cache)",
            "output_tokens": "output tokens",
        }
    )
    passed, total = int(runs.passed.sum()), len(runs)
    questions = ", ".join(sorted(runs.question.unique()))
    return (
        f"# Eval grid results\n\n"
        f"{len(summary)} models, {total} runs, {passed} passed "
        f"({100 * passed // total}%). Questions: {questions}.\n\n"
        f"{table.to_markdown()}\n"
    )


def main():
    if not USAGE_CSV.exists():
        sys.exit(f"no results at {USAGE_CSV} — run the grid first")
    runs = pd.read_csv(USAGE_CSV)
    report = to_markdown(summarize(runs), runs)
    SUMMARY_MD.write_text(report)
    print(report)
    print(f"wrote {SUMMARY_MD}")


if __name__ == "__main__":
    main()

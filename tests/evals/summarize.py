"""Print a model x question table from a directory of Inspect logs.

    uv run python tests/evals/summarize.py tests/evals/logs
"""

import sys
from pathlib import Path

import pandas as pd
from inspect_ai.log import read_eval_log


def summarize(log_dir: str | Path) -> str:
    """Return a markdown table: one row per model, one column per question.

    Each cell is "pass", "fail", or "error" when the run broke before scoring. With
    several runs of the same model and question, the latest log wins.
    """
    rows = []
    for path in sorted(Path(log_dir).glob("*.eval")):  # names start with the timestamp
        log = read_eval_log(path)
        for sample in log.samples or []:
            score = next(iter(sample.scores.values()), None)
            outcome = "error" if score is None else "pass" if score.value == 1 else "fail"
            tokens = sum(u.total_tokens for u in sample.model_usage.values())
            rows.append((log.eval.model, sample.id, outcome, tokens))
    runs = pd.DataFrame(rows, columns=["model", "question", "outcome", "tokens"])
    table = runs.drop_duplicates(["model", "question"], keep="last").pivot(
        index="model", columns="question", values="outcome"
    )
    table["tokens"] = runs.groupby("model").tokens.sum()
    return table.fillna("not run").to_markdown()


if __name__ == "__main__":
    print(summarize(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "logs"))

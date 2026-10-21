# Scientific benchmark

A private set of scientific questions run as the `scientific_benchmark` Inspect task.
Questions, answer keys, judge rubrics and logs are not part of this repository: keep them
outside the repo and outside any environment the agent under test can read.

Question file: a JSON list of `{"id", "category", "question"}`.

```bash
export SCIENTIFIC_BENCHMARK_QUESTIONS=/private/questions.json
# dry run: validate the file, no model calls
uv run python -c "from tests.evals.scientific_benchmark import load_benchmark as l; print(len(l('$SCIENTIFIC_BENCHMARK_QUESTIONS')))"
inspect eval tests/evals/scientific_benchmark.py -T scorer=private_judge.py@judge --model <id> --epochs 3 --log-dir /private/logs
```

`--epochs` repeats each question; runtime, tokens, cost and status are in the Inspect logs
(`inspect view`). The scorer is supplied by the caller, e.g. an Inspect scorer wrapping the
private judge. Live runs call model APIs and may incur costs.

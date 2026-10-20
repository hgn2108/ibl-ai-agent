# Scientific Benchmark Runner

This optional runner evaluates scientific questions using the existing
IBL evaluation actors (Claude, Mistral, and Lightning).

## Privacy

Benchmark questions, answer keys, judge rubrics, and model responses
are not included in this repository.

Questions are loaded from a private JSON file supplied at runtime.
Results should be stored outside the public repository.

## Input format

The private question file is a JSON list:

[
  {
    "id": "example-01",
    "category": "scientific_reasoning",
    "question": "Example scientific question"
  }
]

The model configuration is a JSON object with `provider` and `model`.

## Run

Validate questions without calling a model:

    uv run --no-sync python tests/evals/scientific_benchmark.py --questions /private/questions.json --model-config /private/model.json --output /private/results.csv

Execute selected questions by adding:

    --execute --ids example-01

Live execution may incur API costs.

## Results

The runner records:

- Question ID and category
- Model and completion status
- Execution time
- Input and output tokens
- Cache read and write tokens
- Reported cost and number of turns
- Stop reason and error type

A completed run is not necessarily a scientifically correct answer.
The scientific_score field remains empty until a validated judge
is integrated.

A blank cost means the provider did not report a cost.

## Limitations

The runner sends question text directly to the actor. It does not
automatically load skill packets, enforce dataset isolation, grade
scientific correctness, or save model answers.

It is separate from the nightly CI evaluation pipeline.

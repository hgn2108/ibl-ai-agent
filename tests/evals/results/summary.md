# Eval grid results

15 models x 2 questions, 30 runs, 18 passed (60%).

| model                  | bwm-neuron-count-by-region     | skill-acg-cortical-depth   |   pass % |   input tokens (incl. cache) |   output tokens | cost         |
|:-----------------------|:-------------------------------|:---------------------------|---------:|-----------------------------:|----------------:|:-------------|
| claude-haiku-4.5       | pass                           | pass                       |      100 |                       303445 |            7883 | $0.13        |
| claude-opus-5          | pass                           | pass                       |      100 |                       355854 |            7069 | $0.59        |
| claude-sonnet-5        | pass                           | pass                       |      100 |                       393507 |            4617 | $0.22        |
| Qwen3.8-27B            | fail (max_turns)               | pass                       |       50 |                       188497 |            6823 | not reported |
| deepseek-v4.1-flash    | fail (max_turns)               | pass                       |       50 |                       219406 |            7108 | not reported |
| gemini-2.5-flash       | fail (malformed_function_call) | pass                       |       50 |                        15801 |              15 | not reported |
| gemma-4-31B-it         | fail (answered)                | pass                       |       50 |                       113935 |            3128 | not reported |
| gpt-5-mini             | fail (answered)                | pass                       |       50 |                       111165 |            6567 | not reported |
| gpt-5-nano             | fail (answered)                | pass                       |       50 |                        53261 |            3023 | not reported |
| magistral-small-latest | fail (answered)                | pass                       |       50 |                       111085 |            5818 | not reported |
| ministral-14b-latest   | fail (answered)                | pass                       |       50 |                       163345 |            7205 | not reported |
| ministral-3b-latest    | fail (answered)                | pass                       |       50 |                       155693 |            3873 | not reported |
| ministral-8b-latest    | fail (max_turns)               | pass                       |       50 |                       201240 |            6335 | not reported |
| mistral-medium-latest  | fail (answered)                | pass                       |       50 |                       103954 |            3450 | not reported |
| mistral-small-latest   | fail (answered)                | pass                       |       50 |                        77252 |            3859 | not reported |

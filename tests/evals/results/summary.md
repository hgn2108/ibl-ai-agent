# Eval grid results

15 models, 15 runs, 2 passed (13%). Questions: bwm-neuron-count-by-region.

| model                  |   pass % | how runs ended          |   median turns |   input tokens (incl. cache) |   output tokens | cost         |
|:-----------------------|---------:|:------------------------|---------------:|-----------------------------:|----------------:|:-------------|
| claude-opus-5          |      100 | answered                |              7 |                       219354 |            4195 | $0.56        |
| claude-sonnet-5        |      100 | answered                |              8 |                       278608 |            3742 | $0.14        |
| Qwen3.8-27B            |        0 | max_turns               |             12 |                       183311 |            4709 | not reported |
| claude-haiku-4.5       |        0 | answered                |              6 |                       183876 |            5067 | $0.11        |
| deepseek-v4.1-flash    |        0 | max_turns               |             12 |                       173729 |            2800 | not reported |
| gemini-2.5-flash       |        0 | malformed_function_call |              1 |                        13183 |               0 | not reported |
| gemma-4-31B-it         |        0 | answered                |              4 |                        56717 |            1437 | not reported |
| gpt-5-mini             |        0 | answered                |             12 |                       216679 |            7868 | not reported |
| gpt-5-nano             |        0 | answered                |              5 |                        65487 |            3461 | not reported |
| magistral-small-latest |        0 | answered                |              6 |                        92806 |            4405 | not reported |
| ministral-14b-latest   |        0 | answered                |              3 |                        40538 |            1720 | not reported |
| ministral-3b-latest    |        0 | answered                |             10 |                       147270 |            4269 | not reported |
| ministral-8b-latest    |        0 | answered                |              5 |                        69681 |            2327 | not reported |
| mistral-medium-latest  |        0 | answered                |              6 |                        92092 |            4405 | not reported |
| mistral-small-latest   |        0 | answered                |             11 |                       189498 |            7880 | not reported |

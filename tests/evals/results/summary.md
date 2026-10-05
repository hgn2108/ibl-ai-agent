# Eval grid results

15 models, 15 runs, 2 passed (13%). Questions: bwm-neuron-count-by-region.

| model                  |   pass % | how runs ended          |   median turns |   input tokens (incl. cache) |   output tokens | cost         |
|:-----------------------|---------:|:------------------------|---------------:|-----------------------------:|----------------:|:-------------|
| claude-opus-5          |      100 | answered                |              7 |                       257082 |            5119 | $0.74        |
| claude-sonnet-5        |      100 | answered                |              8 |                       331297 |            3864 | $0.32        |
| Qwen3.8-27B            |        0 | max_turns               |             12 |                       182734 |            6614 | not reported |
| claude-haiku-4.5       |        0 | answered                |              3 |                        70015 |            4116 | $0.13        |
| deepseek-v4.1-flash    |        0 | max_turns               |             12 |                       223848 |            2182 | not reported |
| gemini-2.5-flash       |        0 | malformed_function_call |              1 |                        13183 |               0 | not reported |
| gemma-4-31B-it         |        0 | answered                |              5 |                        70789 |            1512 | not reported |
| gpt-5-mini             |        0 | max_turns               |             12 |                       194156 |            3230 | not reported |
| gpt-5-nano             |        0 | answered                |              3 |                        36706 |            1996 | not reported |
| magistral-small-latest |        0 | answered                |              5 |                        73203 |            3240 | not reported |
| ministral-14b-latest   |        0 | answered                |              5 |                        82529 |            4563 | not reported |
| ministral-3b-latest    |        0 | max_turns               |             12 |                       187646 |            5871 | not reported |
| ministral-8b-latest    |        0 | max_turns               |             12 |                       228509 |           10090 | not reported |
| mistral-medium-latest  |        0 | max_turns               |             12 |                       254299 |           10295 | not reported |
| mistral-small-latest   |        0 | answered                |              5 |                        69289 |            2840 | not reported |

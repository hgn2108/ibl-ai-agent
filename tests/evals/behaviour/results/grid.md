# Behaviour eval grid

3 repeat(s) per cell, 3 models x 3 questions

## Pass rate (%)

| model     |   behaviour-pose-coverage |   behaviour-premovement-trials |   behaviour-zero-contrast-performance |   overall % |
|:----------|--------------------------:|-------------------------------:|--------------------------------------:|------------:|
| haiku-4.5 |                       100 |                            100 |                                   100 |         100 |
| opus-5    |                       100 |                            100 |                                   100 |         100 |
| sonnet-5  |                       100 |                            100 |                                   100 |         100 |

## Token usage and cost (summed over all runs)

| model     |   input_tokens |   output_tokens |   cache_read_tokens |   cost_usd |   median_seconds |
|:----------|---------------:|----------------:|--------------------:|-----------:|-----------------:|
| haiku-4.5 |            426 |           27820 |         1.02239e+06 |     0.4149 |             29.5 |
| opus-5    |            118 |           33645 |         1.29394e+06 |     2.7757 |             43.3 |
| sonnet-5  |            130 |           20444 |         1.81665e+06 |     1.0441 |             27.6 |

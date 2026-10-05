# Behaviour modality eval grid

A small eval grid for the **behaviour** data modality (`bwm_behavior` 2.0.0):
**3 data-loading questions x 3 models**, graded against ground truth computed
from the local dataset, reporting pass rate and token usage per model.

Grading is mechanical. Each model must end its reply with a ` ```json ` block;
those numbers are compared to `ground_truth.json`. No LLM judges the answers, so
a pass means the number was right.

## Results (run 2026-09-28)

3 models x 3 questions x 3 repeats = 27 agent runs, $4.23 total (Q3 revised and re-run 2026-09-28).

| model | pose-coverage | zero-contrast | premovement | overall | cost | median s/run |
|---|---|---|---|---|---|---|
| haiku-4.5 | 100% | 100% | 100% | **100%** | $0.41 | 29.5 |
| sonnet-5 | 100% | 100% | 100% | **100%** | $1.04 | 27.6 |
| opus-5 | 100% | 100% | 100% | **100%** | $2.78 | 43.3 |

Token usage was dominated by cache reads (1.0-1.8M per model) rather than
output (20-34k), because the agent re-reads context on every turn.

**Reading this result.** Accuracy is saturated: these loading paths work across
the whole capability range, and the questions do not separate the models. The
differentiator is cost -- Haiku answered identically for about 1/7 of Opus's
price ($0.046 vs $0.308 per run).

**Limitations, stated plainly.**
- 3 repeats means 100% is "3 for 3", not "never fails".
- The questions are deliberately simple (per the brief), so this says nothing
  about harder analysis work.
- A saturated grid cannot detect small regressions -- the argument for adding a
  harder question next.
- The prompts state the inclusion rules and the answer schema, so this tests
  whether a model can *execute* a specified analysis, not whether it spots the
  pitfall unprompted. That is the honest reason everything passed.
- All three models are Claude, so this is a capability spread within one family,
  not a cross-provider comparison.
- Ground truth for Q1 and Q3 rests on this script alone; only Q2 has an external
  cross-check (the BWM paper).
- `values_match` was changed *after* seeing a run fail: Haiku reported every Q1
  number correctly but omitted `"dlc": 0` for the camera with no DeepLabCut
  sessions. Missing keys now count as 0, which turned that run into a pass. The
  regression test that omitting a *non-zero* key still fails is in this repo,
  and the original reply is in `results/results.json`.

## Files

| File | What it is |
|---|---|
| `compute_ground_truth.py` | Derives the correct answers from the local dataset and writes `ground_truth.json`. The inclusion rule for each question is in its docstring. |
| `ground_truth.json` | The computed answers. Regenerate rather than hand-edit. |
| `questions.json` | The three questions: text shown to models, answer schema, and per-check tolerances. |
| `grader.py` | Extracts the JSON block from a reply and compares it to ground truth. Also builds the prompt. |
| `providers.py` | One function per model provider, all returning `{"reply", "usage"}`. Add an API by adding a function. |
| `run_grid.py` | Runs every question against every model N times, grades, writes `results/`. |
| `results/` | Output of the last run (see below). |

## Running it

Needs the `bwm_behavior` dataset locally and an authenticated Claude CLI
(`claude login`, or `ANTHROPIC_API_KEY`). From the repo root:

```bash
# 1. ground truth (fast, no API calls)
UV_CACHE_DIR=.uv-cache uv run --no-sync python tests/evals/behaviour/compute_ground_truth.py

# 2. the grid (3 models x 3 questions x 3 repeats = 27 agent runs)
UV_CACHE_DIR=.uv-cache uv run --no-sync python tests/evals/behaviour/run_grid.py --repeats 3

# a single model, one run each -- use this to smoke-test changes
UV_CACHE_DIR=.uv-cache uv run --no-sync python tests/evals/behaviour/run_grid.py --repeats 1 --model haiku-4.5
```

Outputs land in `results/`:
- `grid.md` — the pass-rate grid and token table, ready for a slide
- `runs.csv` — one row per (model, question, repeat) with pass/fail, tokens, cost, seconds
- `results.json` — the same plus each model's full reply, for reading *why* a run failed
- `run_log.txt` — console output of the run

To re-grade stored replies after changing `grader.py`, without spending anything
on new API calls, load `results.json` and call `grade()` on each saved reply.

## The three questions and their ground truth

All numbers come from `compute_ground_truth.py` against `bwm_behavior` 2.0.0.
The inclusion rules below are part of each question's text, because a different
rule gives a different correct answer.

### Q1 `behaviour-pose-coverage` (video)

*How many sessions have pose data, per camera and per tracker?*

Counted from `metadata/pose_availability.parquet` rows with `pose_present`,
grouped by camera and `tracker`. A session can have pose on some cameras only.

- 444 of 459 sessions have pose on at least one camera
- leftCamera: 436 Lightning Pose, 1 DeepLabCut
- rightCamera: 432 Lightning Pose, 0 DeepLabCut
- bodyCamera: 253 Lightning Pose, 7 DeepLabCut

**What it tests:** the dataset mixes two pose trackers. A model that reads
`pose_present` and stops reports coverage without noticing the keypoints come
from different algorithms.

### Q2 `behaviour-zero-contrast-performance` (trials)

*Proportion correct on zero-contrast trials, overall and per block prior.*

Zero-contrast trials are those where the presented side carried 0% contrast
(the other side is NaN, so the two columns are combined before testing for
zero). No-go trials (`choice == 0`, 247 of them) are excluded: no report was
made. Correct means `feedbackType == 1`.

- 34,450 trials
- overall: 0.590
- by `probabilityLeft`: 0.2 -> 0.623, 0.5 -> 0.503, 0.8 -> 0.585

**What it tests:** NaN handling in the contrast columns, and the no-go
exclusion. **Sanity check:** the BWM paper reports 58.7% on zero-contrast
trials; this rule gives 59.0%, and the unbiased 0.5 block sits at chance as it
should, since with no prior and no visible stimulus there is nothing to go on.

### Q3 `behaviour-premovement-trials` (trials + wheel)

*Across all sessions, how many trials have their first wheel movement before
stimulus onset, and what fraction of all trials is that?*

`firstMovement_times < stimOn_times`, both from `metadata/trials.parquet`,
pooled over all trials (one denominator) rather than averaging per-session
fractions -- the two differ, so the question text says which is wanted.

- 35,344 of 295,920 trials (11.9%)
- 3,251 trials have no first movement recorded

**What it tests:** `firstMovement_times` is NaN when no movement was detected.
NaN comparisons are False in pandas, so those trials drop out correctly; a
model that fills NaN before comparing inflates the count.

**Why it matters:** these trials are excluded from stimulus-locked analyses,
because movement activity swamps the sensory response, so this fraction is the
share of the dataset lost to that filter.

**Caveat on interpretation:** the task enforces a quiescence period before the
stimulus, so 11.9% is most likely the movement detector picking up small wheel
jitter rather than mice genuinely breaking quiescence. State it as "detected
wheel movement before stimulus onset", not as mice jumping the gun.

**Revision note:** this question originally asked about a single session
(`004d8fd5...`, 270 of 692 trials). That session turned out to be an outlier --
39% against a 9.4% median across sessions -- so the question was broadened to
the whole dataset and re-run on all three models on 2026-09-28. The earlier
single-session version also passed 9/9.

## Design notes

**Why exact grading.** These are data-loading questions with objective answers,
so an LLM judge would add noise and cost for nothing. Counts must match exactly;
proportions allow 0.005 so rounding is not punished. A missing dict key counts
as 0, since an empty category can legitimately be reported either way -- but
omitting a non-zero key still fails.

**Why the answer format is in the prompt.** Models are told the exact keys to
return, so a failure reflects the data work rather than a guess at what shape
was wanted.

**Why repeats.** The answers come from code the model writes on the spot, which
varies between runs. One run cannot distinguish a reliable model from a lucky
one.

**Why providers are agentic.** These questions require executing code against
local data, so a provider needs shell and file tools, not a chat-completion
endpoint. Adding a non-Claude model means giving it an agent loop, which is the
main porting cost when the grid grows to three APIs.

# Behaviour modality — 3-minute talk

## SLIDE 1 — The modality

### Behaviour — `bwm_behavior` v2.0.0 · 459 sessions · 139 mice · 11 labs · 2.9 GB

**The task:** a grating flashes left or right; the mouse turns a wheel to centre it. Correct → reward. In blocks, one side is more likely, so the prior can be used when the stimulus is faint or invisible.

**Three kinds of signal**

- **Trials — event table, not a time series.** 295,920 rows, one per trial: contrast each side, choice, reward, block prior, and 5 event times (stimulus, go cue, first movement, response, feedback)
- **Wheel — continuous time series**, native sampling: position and velocity, plus derived movement/quiescence epochs
- **Video → pose — time series per camera**: keypoint *coordinates* (nose, pupil, paws, tongue), not frames. Left 60 Hz · right 60 Hz · body 30 Hz · 444 of 459 sessions
- Two trackers in one dataset: **Lightning Pose** (nearly all) and **DeepLabCut** (8 camera-sessions)

**Format — two layers, both local, no API calls**

- **Summary layer (154 MB):** parquet tables — per-trial and per-session features. The main interface; loads in seconds
- **Signal layer (2.7 GB):** one zip per session, delta-encoded compressed arrays — the full wheel and pose time series when you need them
- Times in seconds on a common session clock, so neural and behavioural data align
- Derived from the IBL public release; frozen, versioned, checksummed

---

## SLIDE 2 — The eval grid

### Every model answered every question correctly, on all 3 attempts — 27 runs, 100%

Each question was run **3 times on each of the 3 models** (9 runs per question). Model order in the last three columns: **Haiku 4.5 / Sonnet 5 / Opus 5**.

| | Question asked | Correct answer | Where a model can go wrong | Steps | Median time | Cost per run |
|---|---|---|---|---|---|---|
| **Q1**<br>*video* | How many sessions have pose (video keypoint) data, per camera and per tracker? | **444 of 459 sessions.** Left camera: 436 Lightning Pose + 1 DeepLabCut · right: 432 + 0 · body: 253 + 7 | Reporting one session count, missing that **two different trackers** produced the keypoints | 5 / 5 / 8 | 25s / 28s / 36s | $0.04 / $0.12 / $0.26 |
| **Q2**<br>*trials* | On 0%-contrast trials (mouse can't see the answer), how often is it correct — overall and per block? | **59.0% of 34,450 trials.** By block: 62.3% when right side favoured · 50.3% neutral · 58.5% when left favoured | The unshown side is **blank (NaN)**, not zero; and **no-go trials** must be dropped | 6 / 6 / 9 | 34s / 40s / 73s | $0.06 / $0.11 / $0.36 |
| **Q3**<br>*trials + wheel* | Across all sessions, how many trials had wheel movement detected before the stimulus appeared? | **35,344 of 295,920 trials — 11.9%** (3,251 more had no movement recorded at all) | "No movement detected" is stored as **blank (NaN)** — treat it as zero and the count inflates | 5 / 9 / 10 | 22s / 26s / 43s | $0.04 / $0.13 / $0.30 |
| | | | **Total, 27 runs** | | ~40 min | **$0.41 / $1.04 / $2.78 = $4.23** |

- Graded on **numbers, not prose** — model returns JSON, compared to ground truth computed from the data. No LLM judge.
- **Same answers, ~7× the price:** Haiku $0.05/run vs Opus $0.31. Accuracy saturated → cost is the differentiator.
- **Opus consistently slower and pricier for identical answers** — more steps, more time, every question.
- Tokens dominated by **cache reads** (1.0–1.8M) vs output (20–34k) — that's what eval cost scales with.
- Q2 validates the pipeline: paper reports 58.7%, we get 59.0%; unbiased block sits at chance.
- Caveats: 3 repeats = "3 for 3", not "never fails" · a saturated grid can't catch small regressions.

---

## THE SCRIPT

### SLIDE 1 · The modality (~70s)

Behaviour is the mouse side of the Brain Wide Map. The task is simple: a grating
flashes on the left or right, and the mouse turns a wheel to bring it to the
centre. Get it right, get a reward. And it runs in blocks where one side is more
likely — so when the stimulus is faint, or invisible, the mouse can fall back on
that prior. Hold onto that, because one of my questions depends on it.

**What's recorded splits three ways, and they're different kinds of data.**

The **trials** table is an *event* table, not a time series: one row per trial,
296,000 of them, with the contrast on each side, which way the mouse turned,
whether it was rewarded, the block prior, and five timestamps — stimulus, go
cue, first movement, response, feedback.

The **wheel** is a genuine time series at native sampling — position and
velocity throughout the session, plus derived epochs marking when the mouse was
moving or still.

And the cameras give **pose**. Three cameras film the mouse, and a tracker
converts each frame into keypoint coordinates — nose, pupil, paws, tongue. The
video itself isn't in the dataset, only those coordinates, at 60 hertz for the
side cameras and 30 for the body camera, on 444 of the 459 sessions. One detail
that matters later: two different trackers were used, Lightning Pose for
almost everything and DeepLabCut for a handful.

**On format**, there are two layers. A summary layer — 154 megabytes of parquet
tables, per-trial and per-session features, which is the main interface and
loads in seconds. And underneath, a signal layer: one compressed archive per
session holding the full wheel and pose time series, 2.7 gigabytes in total, for
when you need the raw thing. Everything is on a common session clock in seconds,
so it lines up with the neural data. It's frozen, versioned and checksummed, and
it's all local — no API calls.

### SLIDE 2 · The questions (~50s)

*Point at the table as you start.* Each row is one question. Reading across:
what I asked, the right answer, the mistake a model can make, then three columns
of results — steps taken, time, and cost — each showing Haiku, Sonnet and Opus
in that order. Every question was run three times on every model, so nine runs
per question, twenty-seven in total.

I wrote three data-loading questions, each with one objective answer, and each
with a specific way to get it wrong.

**Q1 is the video one:** how many sessions have pose data, broken down by camera
and by tracker? 444 of the 459. The catch is that this dataset was tracked with
two different algorithms — Lightning Pose for almost everything, DeepLabCut for
a handful of sessions. So a single session count looks right but hides the fact
that the keypoints came from two different sources.

**Q2 is the trials one:** on zero-contrast trials — where the stimulus is
invisible, so the mouse genuinely cannot see which side is correct — how often
does it still get it right? 59%. And split by block: when the right side is
the more likely one, 62%; in neutral blocks, 50%; when the left is favoured,
58%. Two catches here. The side that wasn't shown is stored as blank rather than
zero, so you have to handle that. And no-go trials, where the mouse never
responded, have to come out. This question also validates the whole pipeline —
the BWM paper reports 58.7%, we get 59.0%, and the neutral block lands at
exactly chance, which is what it should do when there's no prior to lean on and
nothing to see.

**Q3 joins two tables:** across the whole dataset, how many trials had wheel
movement already detected before the stimulus appeared? 35,000 of 296,000 —
about 12%. This one matters because those trials get excluded from
stimulus-locked analyses: if the mouse is already moving, movement activity
swamps the sensory response. So that 12% is the share of the dataset you lose to
that filter. The catch is that when no movement is detected, the timestamp is
blank — and if you fill those blanks with zero, every one of them looks like an
early movement and your count inflates.

Worth a caveat: the task enforces a quiet period before the stimulus, so 12% is
almost certainly the detector picking up small wheel jitter rather than mice
genuinely jumping the gun. That's the kind of number you'd want to interpret
before trusting.

### SLIDE 2 · The results (~45s)

Twenty-seven agent runs, about forty minutes, $4.23 in total.

Every model passed everything, three times out of three. Grading is mechanical —
the model returns a JSON block, and we compare the numbers to ground truth
computed from the data. No LLM judges anything, so a pass means the number was
right, not that the prose sounded convincing.

The honest reading is that accuracy is saturated. These loading paths are solid
across the whole capability range, and the questions don't separate the models.
What separates them is the last three columns. Haiku gave identical answers for
about a seventh of Opus's price — five cents a run against thirty-one — and it
was faster and took fewer steps on every single question. For routine data
loading, you don't need a frontier model.

One more thing about where the money goes: token usage is dominated by cache
reads, one to nearly two million per model, against only twenty to thirty-four
thousand tokens of output. That's the agent re-reading context every turn, and
it's what eval cost scales with.

### SLIDE 2 · Limits and next (~30s)

Two caveats I want to state rather than bury. Three repeats means 100% is "three
for three," not "never fails." And a grid where everything passes can't warn us
about a regression until it's severe — so the next step is one harder question,
not more easy ones.

The thing that surprised me: because these questions require running code
against local data, a provider needs a full agent loop with shell access. A
plain chat endpoint can't answer them at all. That's the real porting cost as we
add the other two APIs.

---

## IF ASKED

- **Why these three?** The brief said trials *and* video — one each, plus one joining tables.
- **Why is Q3's session unusual?** 39% of trials vs a 9.4% median across sessions. Chosen by a fixed rule (first eid, sorted), not picked after seeing answers. It tests loading, not biology.
- **Why no LLM judge?** Objective answers don't need one; it adds noise and cost.
- **Could a model cheat?** It computes from local parquet; ground truth isn't in the context it reads.
- **Reproduce it?** `tests/evals/behaviour/README.md` has the commands. All 27 replies are saved, so the grader can change and runs be re-scored without new API calls.

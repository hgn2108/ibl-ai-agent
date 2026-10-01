# Package test report: `ibl_aging` 1.0.0, analyst test (Session B)

**Date:** 2026-10-01. **Package:** `/teamspace/studios/this_studio/datasets/ibl_aging/1.0.0`, registered as
`ibl_aging` in `data_locations.local.yaml`. **Question tested:** "Do old mice have lower firing rates than young mice
in the visual cortex?" This was a full exploration → confirmation project, using only the package (plus the paper's
bioRxiv v3 text for one bound). The project record is in this directory (`question.md`, `TODO.md`, `change-log.md`).

**Outcome:** the package supported a complete, locked analysis end to end. The scientific answer is inconclusive
(`confirmatory-analyses/100_results.md`): H1 p = 0.66, equivalence not shown. The package's own `scientific-context.md`
predicted the main obstacle, the sorter/age confound, and the analysis was scoped accordingly to BWM-sorted mice aged
about 90–460 days.

**Second test (added later the same day): reproducing the paper.** Using the authors' public code, the package's spikes
and trials reproduce the paper's visual-cortex firing-rate result to three decimals. The package's own fields
reproduce the paper's QC table (Table 2) at every step except one probe. See "Second test" below; the project is in
`projects/paper_reproduction_aging/`.

## What worked
- **Orientation from the package prose was fast and accurate.** `README.md` and `SUMMARY.md` answered "how many mice and
  sessions" directly (158 / 497, verified against the tables). `scientific-context.md` named the decisive confound
  (sorting × age × lab, r = 0.75) before any data were loaded. Its VIS coverage numbers (84 BWM mice, 16 non-BWM, 15
  mice ≥ 365 d) were right and let the split be designed in one step.
- **Tables are joinable and complete for this question.** `units` → `recordings` (sorter, probe model) → `sessions`
  (age, lab, task duration) → `subjects` (sex) → `channels` (VIS channel counts for yield) → `trials`. No missing keys.
  `sessions.age_at_session_days` and `task_duration_s` saved computation.
- **Spike shards are correct and fast.** About 4 s per probe to decode; counts match `units.spike_count` exactly. The
  53 exploration probes and all confirmation probes were each processed in under a minute. Spikes are not scrambled:
  checked via refractory violations and pairwise unit correlations on a suspicious probe.
- **Per-probe sorter provenance** (`recordings.sorter`, `sorting_release_tag`) made the confound analysable instead of
  hidden.
- **The paper-vs-data notes** in `scientific-context.md` (sorter version, ages) were accurate and saved a detour.

## Where the analysis got stuck
1. **A suspicious old-mouse probe (CSHL067, 646bfb77) could not be resolved.** It has flat stimulus responses, no unit
   below 1.5 Hz, 74 of 91 units labelled VISpm, and 1.68 units per VIS channel against ≤ 0.9 elsewhere. Without
   alignment or histology QC, I couldn't tell a localisation error from biology. It was handled by a post-hoc yield
   rule, reported both ways.
2. **Shard indexing convention.** The repo's BWM example (`skills/ibl-load/references/bwm_ephys_spike_example.md`)
   says `spike_clusters` are dense indices; in this package they are real cluster ids. I caught this only by checking
   `meta.cluster_encoding` and spike counts. Following the example would have silently mislabelled spikes.
3. **The paper's selection and effect sizes were not available.** The paper's ROI table, QC table, inclusion list,
   "2 sessions per region" rule and region-specific age effects (Supplementary Figs. 9–10) are not in the package.
   Fetching them failed: the journal page needs a login, and bioRxiv returned HTTP 429. So the equivalence bound could
   not be based on the paper's effect size, as the user asked; I used a pre-declared ×1.6 per 100 d instead.
   *Resolved later:* all of these are in the authors' public code repository (see "Second test"), which neither the
   package nor `scientific-context.md` points to. The paper's VISp+pm effect is ×1.21 per 100 d, well below the bound
   used.
4. **Whole-recording unit metrics misled.** `firing_rate` and `presence_ratio` cover the post-task period (about 25 min
   on example probes), and rates rise about 2× during the task. On the stored presence ratio, 58% (BWM sorting)
   vs 77% (iblsorter) of VIS units passed the paper's > 0.95 criterion; on a task-window presence ratio the difference disappeared. Every
   task-window metric had to be recomputed from spikes.
5. **Two confirmation mice had VIS units nearly silent in the analysis window** (median 0.001–0.005 Hz in task min
   10–35, against 2–3 Hz stored). This doubled the residual SD and is the main reason the test was inconclusive. Nothing
   in the package's unit metrics would flag it, because they are whole-recording.
6. **`units.drift` is unusable as a drift measure** (medians about 1e5 "µm/hour"). The values follow from brainbox's
   definition (sum of spike-to-spike depth jitter), so this is probably not a conversion error, but the schema
   description invites misuse.

## What the package was missing
All 20 items are in `change-log.md` ("Gaps in the `ibl_aging` 1.0.0 package"); the most consequential first:
| # | missing | consequence here |
|---|---|---|
| 1 | Alignment / histology QC per insertion | CSHL067 region labels unverifiable |
| 3 | The paper's inclusion list | not in the package; it is in the authors' repo, and the package's own fields reproduce it almost exactly (Second test) |
| 4, 19 | The paper's Table 1 (VIS = VISp+VISpm), windows, effect sizes | ROI found only by reading the paper at lock time; equivalence bound not paper-based. All are in the authors' repo, which the package doesn't link |
| 8, 20 | Task-window unit metrics (rate, presence ratio, first/last spike) | silent-in-window units undetected until after the test |
| 9 | Post-task epochs (`epochs` is empty) | can't say what the post-task period is |
| 10 | Non-good units | yield and QC pass rate by sorter not measurable |
| 16 | Correct description of `units.drift` | metric discarded |
| 17 | Probe model as a named confound (62/64 iblsorter probes are 3A) | fourth confound found by the analyst, not documented |
| 18 | Any probe sorted with both sorters | sorter effect not estimable at matched age |
| 2, 5, 6, 7, 11–15 | RIGOR/hardware QC, "2 sessions per region", Table 2, RT definition, sorter version for 16 probes, rig (all null), video covariates, training history, BWM shard doc mismatch | listed in change-log |

## Second test: reproducing the paper's firing-rate analysis (option C)
Project: `projects/paper_reproduction_aging/` (`question.md`, `TODO.md`, `exploratory-analyses/002_results_note.md`).
Method: the authors' code ([repo](https://github.com/Fenying-Zang/Ageing_behavioral_and_neural_variability), commit
`7202a80`, cloned without most LFS data; 6.4 MB of their summary tables pulled for comparison), fed with `ibl_aging`
spikes and trials. Scope: VISp+pm pre/post-stimulus firing rate; the all-region run was skipped at the user's request.
- **Inclusion (R0):** all 18,755 of the paper's neurons are in the package (matched by `cluster_uuid`), on the same 501
  probes, with identical ages; region labels agree for 99.88%. Trials are identical in 365 of 367 sessions. KS046
  `69c9a415` differs in every trial (up to 48 s) and in count, with the same revision label (2025-03-03), so
  **the ingestion side should check that session's trials extraction**.
- **Statistics (R1):** the authors' code on their own table reproduces their published β and p_perm exactly.
- **Per-neuron FR (R2):** recomputed from package spikes and trials, 95.3% of 6,462 neuron × contrast rows are
  identical (r = 0.99997). The differences come from trial-NaN patterns in 4 sessions, plus about one-spike
  differences from the package's 100 µs spike-time snapping.
- **Result (R3):** VISp+pm pre_fr β = 0.698–0.699 ln Hz/yr (paper 0.697), p_perm = 0.032 (paper 0.032); post_fr β = 0.539
  (paper 0.538), p_perm = 0.045–0.047 (paper 0.048).
- **Data provenance:** all data values came from the package. In R2–R3 the *session selection* came from the authors'
  367-session trials file. R4 then tested selection from package fields alone.
- **Package-only selection (R4):** the authors' QC steps on package fields reproduce their Table 2 exactly for the new
  release (38 sessions / 64 probes at every step) and for BWM, except one extra session/probe at the ROI step (330/440
  vs 329/439, region-label difference). The package's BWM probes equal the authors' `2023_12_bwm_release` freeze. The
  authors' alignment and Alyx-QC queries remove nothing, so gaps 1–2 do not block this reproduction. The package-only
  set (504 probes) contains all 501 final probes; the last step (task-window unit QC, 503 → 501) needs spikes for every
  probe and was not rerun.
- **Unit selection:** the paper's final neuron QC uses task-window FR/PR, not the stored whole-recording metrics. Only
  16,637 of its 18,755 neurons pass the package's stored `firing_rate`/`presence_ratio`; recomputing the task-window QC
  from package spikes recovers the paper's VISp+pm set (718 of 718, plus 2). This reinforces gap 8/20.
- **Consequence for the first test:** the paper's effect (×1.21 per 100 d) lies inside our inconclusive 95% CI
  (×0.35–×1.96). The two analyses don't conflict; the mouse-level test had no power for an effect this size.

## For the ingestion side to check
- **`units.drift` (gap 16):** compare `clusters.metrics.pqt` `drift` from source against `units.drift` for a few
  probes. They should match exactly, since `convert.py` line 139 copies it. Then fix the schema description to state
  the brainbox definition, `sum(|diff(spike depths)|) / duration × 3600`, which scales with firing rate (Spearman
  0.86). Optionally add a per-probe physical drift (`electrode_drift.estimate_drift`).
- **Add to `scientific-context.md`:** probe model co-varies with sorter and age; the paper's VIS ROI is VISp+VISpm;
  rates rise during the task and some units are absent for long stretches, so whole-recording unit metrics are a
  poor guide to task-period activity.
- **Consider shipping per-unit task-window metrics:** rate, presence ratio, first and last spike time within the task.
- **Trials of KS046 `69c9a415`:** every trial differs from the authors' table (same revision label). Check which
  extraction each used.
- **Link the authors' code repository** in `scientific-context.md` ("Papers"). It holds the inclusion lists, the ROI
  table, the QC table and the per-region effect sizes.

## Process notes (agent)
- The analysis used `uv run` throughout. Pilot issue 11 says to use `.venv/bin/python` while spikepack is outside the
  lockfile, but the rule lives only in `ingestion-notes.md`, which an analysis session has no reason to read.
  spikepack survived (checked). The rule should be in `AGENTS.md` or the install skill if it applies to analysis too.
- Mistakes caught and corrected during the session: a whole-dataset correlation computed before the split (disclosed in
  change-log); "every task ≥ 37 min" (true only for exploration; 2 confirmation sessions were shorter, and a rule was
  added from durations only); table and print bugs in scripts (fixed before the results were used).

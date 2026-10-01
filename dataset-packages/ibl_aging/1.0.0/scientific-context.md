# Scientific context

Main source: Zang et al., *Nature Communications* 17, 8156 (2026),
doi:10.1038/s41467-026-74227-1 ("the paper"). Read on 2026-10-01 from the article web page;
quotes are from its text. Where the paper and this package's data disagree, see
"Paper vs data" below.

## Aim
The paper asks "how ageing affects behavioural and neural variability" during visual
decision-making. Its starting hypothesis: "Age-related cognitive decline in learning and
decision-making may arise from increased variability of neural responses." It tests age
effects on firing rates, Fano factors and stimulus-induced variability quenching across
16 brain regions, with age as a continuous predictor.

The aim and the criteria below were read from the published paper. The findings list
below is from the preprint abstract (v1, 2025-08-27) and was not re-checked against the
published results:
- Older mice have more variable response times.
- Older mice have higher firing rates and higher post-stimulus variability.
- Older mice show less stimulus-induced variability quenching.
- Region effects differ: firing is higher in visual and motor cortex, striatum, midbrain
  and hippocampus, and lower in thalamus.

The user stated no hypotheses beyond the paper.

## How the paper selected its data (not applied in this package)
This package carries all 497 tagged sessions and all good (`label == 1`) units. The paper's
analysis set is a subset: 149 mice, 367 sessions, 503 insertions and 18,755 neurons in 16
regions. To reproduce it, apply its criteria in the analysis:
- **Sessions:** "more than 400 trials and at least 90% accuracy on 100% contrast trials";
  at least 3 incorrect trials after the trial filter; hardware tests passed; visual
  inspection for drift, epileptiform activity, noisy channels and artefacts (RIGOR);
  insertions with resolved alignments; sorting by "the same version of the ibl-sorter
  algorithm (version 2.35.0)" (but see "Paper vs data").
- **Trials:** "only the first 400 trials of each session"; trials missing `choice`,
  `probabilityLeft`, `feedbackType`, `feedback_times`, `stimOn_times` or
  `firstMovement_times` are dropped; RTs outside 0.08–2 s are dropped.
- **Neurons:** the three single-unit QC metrics pass (this package's `label == 1`), plus
  "average firing rate greater than 1 spike/s" and "presence ratio exceeded 0.95"
  (`units.firing_rate`, `units.presence_ratio`), within the paper's 16 regions (its Table 1,
  not copied here).
- **Age groups:** "for visualization" only, young (N = 97 mice, mean 5.60 months) and old
  (N = 52, mean 12.07 months), split at 7.6 months, "mean age in the dataset". The
  analyses use continuous age. This package defines no groups.

## Caveats from the design
- **Age is compared across subjects, so N is the number of mice.** There are 158 mice,
  but only 21 have any session past 365 days. Neurons, probes and sessions within a mouse
  are not independent. The paper fits GLMs on single-neuron metrics without random effects
  and handles the hierarchy by permutation, "shuffling age labels at the session level";
  a mouse-level treatment is stricter.
- **Recording quality differs with age.** The paper reports "neural yield was slightly
  reduced in older mice" (β_age = −0.106, p = 0.001), "specifically in PPC, LS, and ACA",
  attributed to "increased tissue and dural rigidity" and "possible regional-specific
  neuronal loss". Compare yield, stability and drift by age before claiming a neural age
  effect.
- **Spike sorting differs between the BWM and the old-mouse probes, and sorting is
  strongly confounded with age.** Each probe uses the sorting its release tags
  (`recordings.sorter`):
  - the 699 BWM probes (459 sessions, 139 mice, age 92–461 d, median 182): ALF collection
    `pykilosort`, revision 2024-05-06, tag `2024_Q2_IBL_et_al_BWM_iblsort` ("Spike sorting
    output with ibl-sorter 1.7.0 for BWM"); the sorter log says "Starting Pykilosort
    version 1.7.0"; files created 2024-05;
  - the 64 non-BWM probes (38 sessions, 19 mice, age 317–597 d, median 530): collection
    `iblsorter`, unrevisioned; Alyx records `iblsorter_1.9.1` for 46 and `iblsorter_1.9.0a`
    for 2, and only `3.2.0` (probably the ibllib version, sorter version unknown) for 16;
    files created 2024-09 to 2025-01.

  So the difference is most likely between versions of the same sorter (1.7.0 vs 1.9.x)
  rather than between two programs, but it is still a processing difference, and the paper
  states the opposite (see "Paper vs data"). No session or mouse has both, and r(age,
  non-BWM sorting) = 0.75. Among sessions at ≥365 d, 73 % use the non-BWM sorting; at
  ≥450 d, 90 % (27 of 30). The non-BWM sessions are also 36/38 churchlandlab, 2/38
  mrsicflogellab, all recorded in 2020, so sorting, lab mix and recording year move
  together with age.

  Measured in this package: good units per probe average ≈ 108 for the BWM sorting
  (75,708 on 699 probes) and ≈ 60 for the non-BWM sorting (3,863 on 64). This is not
  interpreted, since age and lab differ too. Label QC is applied to each sorting's own
  metrics, so the same threshold may select different populations. A firing-rate or
  variability difference between "old" and "young" can therefore be a sorting effect. To
  address it:
  - include `recordings.sorter` (and lab) as a covariate, or restrict to
    `sessions.in_bwm_release`;
  - know that the BWM-only restriction leaves little old data: 9 mice with a session
    ≥300 d and 1 mouse ≥450 d. The oldest ages are then effectively non-BWM-sorting-only
    and can't be separated from sorting within this package;
  - compare unit yield and QC pass rate by sorting before any age claim.

  The paper reports robustness to "differences between dataset sources or lab-specific
  environmental factors (Supplementary Figs. 6 and 7)"; dataset source is the same split as
  sorting here. A clean fix needs all probes on one sorter version upstream (see open
  questions).
- **12 labs: lab is a real source of variation** and is not balanced across age. Model it
  or stratify by it. The paper's main models have no lab term.
- **Training duration is correlated with age.** The paper notes "neural differences could
  reflect older animals having followed a longer training trajectory rather than
  chronological age per se" and reports age effects "essentially unchanged after adding
  training duration". Training sessions are not carried in this package.
- **Movement modulates neural activity.** The paper adds "video-derived movement
  covariates (paw speed, nose-tip speed)"; they add explanatory power but "age effects
  persisted". Video and pose are referenced in place here, not converted.
- **Sessions span 2019–2023, and a mouse may have up to 13 sessions over up to 151 days.**
  Expect drift across sessions and across rig or software versions (iblrig 6.1–6.6). Don't
  pool sessions naively. Age and recording date are correlated.
- **Region coverage may differ by age.** BWM targeted many regions, and the old-mouse
  additions may not cover them evenly. A region difference can look like an age
  difference. Compare age within region. Example, visual cortex (Beryl `VIS*`): 3,093 good
  units from 84 mice in BWM sessions and 267 from 16 mice in non-BWM sessions; 15 mice have
  VIS units in a session at ≥365 d.
- **IBL task with biased blocks.** `probabilityLeft` is meaningful and
  `skills/ibl-analyze/references/prior_and_block_semantics.md` applies. The first 90
  trials of each session are unbiased (0.5).
- **No trial inclusion mask.** BWM's `bwm_include` is not borrowed, so declare any trial
  exclusion in the analysis (the paper's is above).
- **Units are pre-filtered to `label == 1`** (user's choice). This is the first of the
  paper's three neuron criteria; the firing-rate and presence-ratio criteria are not
  applied. Spikes of units with `label < 1` are not in the package.
- **`skills/ibl-analyze/` QC and reproducibility guidance comes from BWM evidence.** It
  covers the 699 BWM probes here but not the 64 non-BWM probes.
- **About 92 % of sessions are BWM.** A BWM result reproduced here is not independent
  evidence.

## Other known confounds
- The sorting/age/lab confound above (found in the data during ingestion).
- From the paper: training duration, movement, and age-related neural yield (above).
- Rig changes, surgery problems, cohort effects: none known to the user beyond the paper.
  `rig` is not recorded in this package. Surgery is described in another publication the
  paper cites (its Appendices 2 and 3), not read here. Open questions for the authors are in
  `ingestion/open-questions.md`.

## Paper vs data
Found during ingestion, 2026-10-01:
1. **Sorter version.** The paper: "All sessions were spike sorted using ibl-sorter
   (version 2.35.0), matching the version used for the original IBL dataset processing."
   The data: BWM sorting is pykilosort/ibl-sorter 1.7.0 (log and tag); `2.35.0` is the Alyx
   `version` field of those datasets, most likely the ibllib version that registered them.
   The non-BWM probes record iblsorter 1.9.0a/1.9.1 (48) or an unknown version (16), sorted
   months later. The public data does not show one sorter version across all probes.
2. **Old-mouse ages.** The paper: 19 new mice, "11 male, mean age = 16.58 months, range
   10.58–19.90 months". The package: 19 mice, 11 male, session ages 10.41–19.61 months
   (mean 16.19; per-mouse mean 16.34), using months = days / 30.44. The sex and mouse counts
   agree; the ages differ slightly, perhaps from a different age definition or session subset.
3. **BWM mice.** The paper: 130 mice (89 male), 3.10–15.13 months, after its QC. The
   package: 139 mice (94 male), 3.02–15.15 months, before QC. Consistent with a QC subset.

## Papers
- Zang F., Khanal A., Förster S., International Brain Laboratory, Churchland A. K.,
  Urai A. E. *Age-related changes in behavioural and neural variability in a
  decision-making task.* Nature Communications 17, 8156 (2026).
  doi:10.1038/s41467-026-74227-1 (DOI built from the article URL; the fetched page did not
  print it). The data-availability statement was not read.
- Preprint: bioRxiv doi:10.1101/2025.08.22.671763 (v1 2025-08-27, v2 2026-02-27, v3
  2026-08-18). The release tag `2025_Q3_Zang_et_al_Aging` cites the preprint DOI.
- International Brain Laboratory, Brain Wide Map release (source of 459 of the sessions).

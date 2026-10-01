# ibl_aging 1.0.0

> **Build status: built 2026-10-01** (counts in `SUMMARY.md`). Registered as `ibl_aging` in
> this Studio's `data_locations.local.yaml`; not yet published.

## Summary
Neuropixels recordings and behaviour from 158 C57BL/6 mice (105 M, 53 F), aged 92–597
days at recording (median 186). There are 497 sessions and 767 probe insertions from
12 IBL labs, recorded 2019-11 to 2023-10. All mice ran the IBL visual decision-making
task (`ephysChoiceWorld`, with biased blocks). The study asks how age changes
behavioural and neural variability: response-time variability, firing rates, and
stimulus-induced variability quenching across brain regions (Zang et al., Nature
Communications 2026, doi:10.1038/s41467-026-74227-1). It is a superset of the Brain Wide Map release: all 459
BWM sessions and 699 BWM probes, plus 38 sessions and 68 probes from old mice
(317–597 days).

## Scope
- Source: OpenAlyx release tag `2025_Q3_Zang_et_al_Aging`. Spike sorting for the 699 BWM
  probes comes from `2024_Q2_IBL_et_al_BWM_iblsort`, because the aging tag carries none.
- Materialised: subjects, sessions, recordings, trials, events, good units (`label == 1`),
  channels with brain regions, and spike shards of good units.
- Referenced in place: LFP, raw ephys, video, pose, wheel, licks, motion energy.
- 4 of the 68 extra probes have no spike sorting upstream, so they have no spikes.

## When to use
- Questions about age as a continuous covariate of behaviour or single-unit activity in
  the IBL task.
- Old-mouse (>300 days) recordings that are not in BWM.

**Main caveat for any age question:** the BWM probes and the 64 old-mouse probes were
spike-sorted with different sorter versions, so sorting is confounded with age (and lab).
Read `scientific-context.md` before analysing.

## When not to use
- As an independent replication of BWM results: about 92 % of its sessions *are* BWM.
- Genotype or line comparisons: none are recorded.
- Analyses that need units failing IBL QC, spike amplitudes or waveforms: they are not
  carried.

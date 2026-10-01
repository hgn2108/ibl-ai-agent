# Experiment

## Subjects
158 mice, strain C57BL/6. The strain comes from the user, citing the paper; Alyx doesn't
record it. Line, genotype and cohort are not stated. There are 105 males and 53 females.
Date of birth is known for all subjects, and age at recording ranges from 92 to 597 days.
Subjects were housed and trained in 12 labs: angelakilab, churchlandlab,
churchlandlab_ucla, cortexlab, danlab, hausserlab, hoferlab, mainenlab, mrsicflogellab,
steinmetzlab, wittenlab and zadorlab.

## Surgery
Not stated in the documentation read during ingestion. See the paper's methods.

## Apparatus
Head-fixed mice turn a steering wheel to move a visual grating. Behaviour runs under
iblrig/Bpod. Neural data are from Neuropixels probes, 1 or 2 per session. Alyx model codes are 3B2
(590), 3A (173) and NP2.4 (4). Three cameras (left, right,
body) record video.

## Protocol
`_iblrig_tasks_ephysChoiceWorld`, iblrig versions 6.1.3 to 6.6.4, or unversioned; the
per-session value is in `sessions.protocol`. A grating appears on the left or right at
one of several contrasts. The mouse reports its side by turning the wheel. Correct
choices are rewarded (`rewardVolume`, µL). Spike times continue past the last trial, and `raw_passive_data` exists for at least
one sampled session. Passive-protocol data are not carried in this package.

## Design and factors
- **Age**: continuous, in days (`sessions.age_at_session_days`). It is mostly a
  between-subject factor: within one mouse, age spans at most 151 days. No age groups
  are defined in the package.
- **Sex**: between-subject, M/F.
- **Intended comparison**: behavioural and neural variability as a function of age,
  across brain regions.
- **Statistical unit**: subject.

## Trial structure
Trial-based. Each trial has a start (`intervals_0`) and an end (`intervals_1`), a
stimulus (`stimOn_times`, `contrastLeft`/`contrastRight`), a response (`choice`,
`firstMovement_times`, `response_times`) and an outcome (`feedbackType`,
`feedback_times`). Biased blocks: `probabilityLeft` is 0.5 for the first 90 trials,
then alternates between 0.2 and 0.8 blocks. This was measured in all 497 sessions
(`trials.probabilityLeft`).

## Session schedule
1–13 recording sessions per mouse (median 3), between 2019-11-26 and 2023-10-19.

## Training history
Not stated in the documentation read during ingestion. Training sessions are not
carried in this package.

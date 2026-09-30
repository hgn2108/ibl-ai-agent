# IBL trials extraction

Load this only when the package's `schema.yaml` declares
`task: ibl_choice_world`. For any other task, or none, never call the existing
extraction. It encodes the IBL trial structure, so applied to another task it
would produce columns that mean something other than their names. Instead,
declare the dataset's own `trials` table in `schema.yaml` and build it in
`ingestion/convert.py`.

Within the gate, reuse the extraction (`bwm_simple._build_trials`) and do not
write a parallel one. The thing most likely to drift is which columns a trials
table has, and a parallel builder would duplicate exactly that.

## Columns
**Required.** These define the trial: its extent, stimulus, response and
outcome. If one is missing, it is an error and ingestion stops.
`eid`, `intervals_0`, `intervals_1`, `stimOn_times`, `contrastLeft`,
`contrastRight`, `choice`, `feedbackType`

**Optional.** If one is missing, skip it and record the skip in both
`ingestion-log.md` and `open-questions.md`. These vary by rig, protocol and
release.
`probabilityLeft`, `bwm_include`, `goCue_times`, `firstMovement_times`,
`response_times`, `feedback_times`, `goCueTrigger_times`, `stimOff_times`,
`rewardVolume`, `reaction_time`

`feedbackType` is required but `feedback_times` is not. What happened defines
the trial; when it happened is just an event time. `trial_id` is computed inside
the extraction, not read from the input.

## Constraints
- **Keep the column order canonical**, dropping absent optional columns where
  they sit. Reordering would break BWM's byte-identical output, which shares
  this code.
- **Write `probabilityLeft` only if the documentation confirms biased blocks.**
  Otherwise write neither it nor any block-derived column, and say so in
  `scientific-context.md`.
- **`bwm_include` is BWM's trial mask. Do not borrow it.** Declare the package's
  own inclusion rule in `schema.yaml`.
- Generic tables key on `session_id`, while the extraction keys on `eid`. Map
  between them at the call site; do not rewrite either side.

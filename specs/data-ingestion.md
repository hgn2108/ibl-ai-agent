# Spec: Generic data ingestion and standardised dataset packages

## Status
Approved
2026-09-30

## Problem
The agent can only analyse the IBL Brain Wide Map, because BWM's task description,
scientific context and data layout are hard-coded across `AGENTS.md`, `skills/` and
`docs/bwm/`. Analysing the IBL aging and autism datasets — and later any lab's
neurophysiology data, including experiments that are not trial-based — requires a
repeatable way to turn a documented raw dataset into a self-describing **dataset
package** that a later agent can analyse without re-reading the raw source. This
spec covers the ingestion skill that writes such packages, the package contract
itself, and the minimum repo changes needed to read them, while leaving BWM's data,
schemas and analysis guidance untouched and BWM's builder output byte-identical.

## Inputs

### Raw dataset and its documentation
- Source data in its original form. Verified target for the pilot: IBL aging and
  autism datasets, reachable through ONE/Alyx, not yet compressed into shards.
- Whatever documentation accompanies it: papers, README, lab notes, NWB metadata.
- Type: arbitrary. No format is assumed by the contract.

### User answers
- Free-text responses to questions the skill asks when a required fact is absent
  from the source documentation.
- Constraint: the skill never substitutes an inferred value for a blocking fact
  (see Behavior → Minimum viable package).

### Repo files read (unmodified by this change)
- `ibl_ai_agent/data_locations.py` — `resolve_dataset_dir(name)`,
  `find_dataset_versions(name)`, `DataLocationError`. Already dataset-name generic:
  a dataset is any root containing `schema.yaml`, or version directories containing
  `schema.yaml`.
- `ibl_ai_agent/datasets/bwm_shared.py` — `compress_array`, `decompress_array`,
  `write_array_directory`, `read_array_directory`.
- `reports/datasets/bwm_ephys/1.2.1/schema.yaml` — the existing `tables:` /
  `stores:` shape the package contract extends. A local build output (`reports/*` is
  gitignored), not a tracked file; the same shape is produced by `_build_schema` in
  `ibl_ai_agent/datasets/bwm_ephys.py`.

### External dependency
- `spikepack`, `int-brain-lab/spikepack`, MIT. Version `0.1.0` at commit
  `30ab06ff7794d89cab17cb54338db869ad90d036`. Public API used: `write_blosc`.
- `write_blosc(path, *, times_seconds, labels=None, cluster_ids=None,
  quantization_us=100, extra_meta=None) -> int`.
- Package dependencies: `numpy`, `numcodecs`. `requires-python = ">=3.11"`.
- Not on PyPI: `https://pypi.org/pypi/spikepack/json` returns 404 for both
  `spikepack` and `spike-pack` as of 2026-09-29. Install is from git.
- Installed only through the `ingest` optional-dependency extra, which carries the
  environment marker `python_version >= '3.11'`. The repo's own
  `requires-python = ">=3.10"` (`pyproject.toml:10`) is unchanged, so on 3.10 the
  extra resolves to nothing and no ingestion code is importable.

### Per-session ONE trials
- Source for the aging and autism `trials` tables: `trials` objects loaded per
  session through ONE. Neither dataset has the BWM release trials aggregate parquet
  that `bwm_simple._resolve_aggregate_table` fetches, nor a BWM-style roster.
- Loaded by `ibl_ai_agent/datasets/one_trials.py` (Behavior → 2, step 6).

## Outputs

### A dataset package
Written to `<dataset_root>/<dataset_name>/<version>/`, registered in
`data_locations.local.yaml` under `datasets:`. Contents as defined in
`project-structure.md`:

- `README.md`, `experiment.md`, `modalities.md`, `scientific-context.md` (optional in
  general; required for the IBL aging and autism packages, see Behavior → 3)
- `schema.yaml`, `provenance.yaml`, `manifest.json`, `SUMMARY.md`
- `metadata/` — core tables `subjects`, `sessions`, `recordings`, `events`,
  `epochs`; conditional tables `units`, `channels`, `trials`
- `features/` — optional
- stores of kind `spike_shards`, `timeseries`, or `referenced_in_place`
- `ingestion/convert.py`, `ingestion/ingestion-log.md`,
  `ingestion/open-questions.md`

Constraints:
- `schema.yaml` declares `contract_version: 1` — the version of the generic package
  contract — alongside the existing per-dataset `schema_version`, which keeps its
  current meaning of "version of this dataset's own layout".
- `schema.yaml` declares `task` and, where the source records one, `task_protocol`.
  `task: ibl_choice_world` is what gates reuse of the BWM trials extraction
  (Behavior → 2, step 6); `task_protocol` records the iblrig protocol string and is
  what decides whether `probabilityLeft` is written.
- `events.event_time` is float64 seconds in the table's declared `time_base`.
- Every column of every declared table and store declares a `units` key. `a.u.`
  and `dimensionless` are valid for quantities; `null` is valid only for identifier,
  categorical, boolean and string columns.
- Every table and store names a `time_base` declared in `time_bases:`.
- Spike shards are written by `spikepack.write_blosc` with all spike times snapped
  to the quantization grid (Behavior → 4).

### Repo changes
Enumerated in Behavior → Change surface.

## Behavior

### 1. Package contract
`project-structure.md` is the normative description of the package layout,
`schema.yaml` and `provenance.yaml` contracts, core and conditional tables, store
kinds, minimum viable package, and versioning. This spec does not restate it.

### 2. Ingestion skill
New skill `skills/ibl-ingest/SKILL.md`, marked **v0**: written from this spec and
to be revised from the pilot's `ingestion/ingestion-log.md` and
`ingestion/open-questions.md` once the aging and autism packages are built. The v0
marker sits in the skill's own header so a later reader knows it has not yet been
exercised. Steps:

1. Read the raw dataset and its documentation.
2. Draft `README.md`, `experiment.md`, `modalities.md` from what the documentation
   states.
3. Identify blocking gaps. Ask the user. Do not infer. The skill leads: it asks for
   what it needs rather than expecting the user to know. Generic checklist, asked
   only where the documentation does not already answer it:
   - a paper, preprint, thesis chapter or methods text describing the experiment;
   - a description of each data file: what it contains, its units, and its clock;
   - how clocks are synchronised across devices;
   - whether the experiment is trial-based, and if so what defines a trial;
   - which task was run, and which protocol — recorded as `task` and
     `task_protocol` in `schema.yaml`. `task` decides whether the BWM trials
     extraction is reused at all (step 6); `task_protocol` decides whether the
     protocol uses biased blocks, and so whether `probabilityLeft` and every
     block-derived behaviour column are written, and whether
     `skills/ibl-analyze/references/prior_and_block_semantics.md` applies
     (Behavior → 3);
   - subject metadata: line, genotype, sex, date of birth, cohort;
   - the source-selection rule (which units or ROIs were kept, and why);
   - the experimental design: which factors are manipulated or measured, at what
     grain, and what comparison the experiment was built for.
   Every question asked and its answer go in `ingestion/ingestion-log.md`.
4. Measure and estimate before converting anything in bulk. Measure raw size per
   session, then write shards for 2–3 sessions and measure the result. Estimate the
   full run from those measurements and present the estimate to the user before
   starting it. This is the repo's existing "Start small" policy (`AGENTS.md`)
   applied to ingestion, not a new rule. The outcome decides whether spikes are
   converted to shards or referenced in place, so it precedes `schema.yaml`, which
   declares the store kinds.
5. Write `schema.yaml` — `contract_version`, tables, stores, `time_bases`,
   `reference_frames`, `design`, per-column `units`.
6. Materialise the metadata tables as parquet. For the IBL aging and autism
   packages the `trials` table and its reshape into `events` reuse the existing
   `bwm_behavior` extraction — `bwm_simple._build_trials`
   (`ibl_ai_agent/datasets/bwm_simple.py:276`) and `bwm_ephys._build_events`
   (`ibl_ai_agent/datasets/bwm_ephys.py:907`), the pair `bwm_behavior` itself calls
   at `ibl_ai_agent/datasets/bwm_behavior.py:299-301` — generalised to cover the
   non-BWM case rather than duplicated.

   Input. `ibl_ai_agent/datasets/one_trials.py` loads the `trials` object for each
   session through ONE and returns one concatenated DataFrame carrying an `eid`
   column, which is what `_build_trials` consumes. Aging and autism have neither the
   BWM release trials aggregate parquet that
   `bwm_simple._resolve_aggregate_table` fetches nor a BWM-style roster, so this
   loader is the only new extraction code. The package's `ingestion/convert.py`
   calls it; it does not reimplement it.

   `_build_trials` changes. It accepts either a path or an already-loaded DataFrame
   as its trials input, `roster` becomes optional, and the fixed `ordered` column
   list splits into required and optional groups. With `roster=None` the roster
   filter and merge are skipped and the roster-derived columns (`subject`, `date`,
   `session_number`, `lab`) are not emitted. BWM's call site passes a path and a
   roster as it does today, so BWM output is unchanged.

   **Gate.** `_build_trials` is reached only for packages whose `schema.yaml`
   declares `task: ibl_choice_world`. A package that declares any other task, or no
   task, never calls it; a generic trials builder for non-IBL tasks is out of scope.

   **Required columns** — the minimal set that defines an IBL trial: its extent, its
   stimulus, the animal's response, and the outcome. A missing required column is an
   error; ingestion stops.

   - `eid` — session key, also how trials are grouped to number `trial_id`
   - `intervals_0`, `intervals_1` — trial extent
   - `stimOn_times` — stimulus onset, the alignment event the task is built around
   - `contrastLeft`, `contrastRight` — the stimulus
   - `choice` — the animal's response
   - `feedbackType` — the outcome

   **Optional columns** — every other BWM trial column. A missing optional column is
   skipped, not an error, and the skip is recorded in both
   `ingestion/ingestion-log.md` and `ingestion/open-questions.md`.

   - `probabilityLeft` — block prior; also gated on the protocol (below)
   - `bwm_include` — BWM's trial mask, with no aging/autism analogue
   - `goCue_times`, `firstMovement_times`, `response_times`, `feedback_times`
   - `goCueTrigger_times`, `stimOff_times`, `rewardVolume`, `reaction_time`

   `feedbackType` is required while `feedback_times` is not: what happened defines
   the trial, when it happened is an event time like the others, and `_build_events`
   already skips event source columns that are absent
   (`ibl_ai_agent/datasets/bwm_ephys.py:911-913`).

   `trial_id` is computed inside the function, not read from the input, and is
   neither required nor optional.

   **Ordering constraint.** The emitted column order stays the current canonical
   order with absent optional columns dropped in place — not required columns
   followed by optional ones. BWM supplies every column in both groups, so its
   output column order and contents are unchanged, which is what acceptance
   criterion 6 asserts.

   `_build_events` changes. It gains keyword-only `event_time_dtype`, defaulting to
   `np.float32` so BWM output is unchanged, and keyword-only control of the session
   key column and the carried columns. Ingested packages pass `np.float64`, which is
   how the float64 `event_time` requirement is met — the cast is inside the function
   (`ibl_ai_agent/datasets/bwm_ephys.py:920`), so up-casting its output afterwards
   would not recover the precision. BWM keeps float32 and is not retrofitted (Out of
   scope).

   Both functions keep keying trials on `eid`. The generic tables key on
   `session_id`, mapped as in Behavior → 7, at the call site.

   `probabilityLeft` (`ibl_ai_agent/datasets/bwm_simple.py:294`) is meaningful only
   under the biased-block full task. Neither it nor any block-derived behaviour
   column is written unless the documentation gathered in step 3 confirms the
   protocol uses biased blocks.

   `bwm_include` (`ibl_ai_agent/datasets/bwm_simple.py:304`) has no aging/autism
   analogue (audit item 6 in `ingestion-notes.md`); the inclusion rule is declared
   in the package's own `schema.yaml` instead.
7. Convert spikes to shards via `spikepack.write_blosc`, at the scale approved in
   step 4.
8. Reference LFP and video in place, recording re-resolution keys.
9. Write `provenance.yaml`, `manifest.json`, `SUMMARY.md`,
   `ingestion/convert.py`, `ingestion/ingestion-log.md`,
   `ingestion/open-questions.md`.
10. Register the package in `data_locations.local.yaml`.

### 3. Minimum viable package
Ingestion stops and asks rather than shipping without: `dataset_name`,
`dataset_version`, the `README.md` summary, a declared time base, units for every
column of every declared table and store, `subjects` and `sessions`,
`provenance.source`, and for every declared store either materialised data or a
re-resolvable reference.

Ingestion may ship, recording an entry in `ingestion/open-questions.md`, without:
`scientific-context.md` (except for the IBL aging and autism packages, below),
`features/`, per-column prose beyond units, exact conversion detail for
upstream-derived fields, optional modalities.

For the **IBL aging and autism packages `scientific-context.md` is required and
blocking.** This is a pilot-specific requirement on those two packages, not a
change to the package contract: `project-structure.md` keeps the file optional in
general. It must carry, from the audit in `ingestion-notes.md`:

- **audit item 9** — `skills/ibl-analyze/references/reproducibility_qc.md` is
  framed entirely on cross-**lab** reproducibility. These datasets are plausibly
  single- or few-lab, making lab a degenerate variance dimension, and that file's
  robust/fragile lists are evidence from BWM repeated-site recordings, not a
  general law.
- **audit item 10** — subject is an experimental factor here, not only a coverage
  dimension: age is a continuous between-subject covariate and genotype a
  between-subject factor. **In a between-subject comparison N is subjects**, and
  typically small.
- **audit item 11** — **age or genotype may be confounded with recording quality**
  — yield, stability, drift, engagement — so QC must be reported and compared by
  group before any apparent neural group difference is claimed.
- **audit item 12** — whether the protocol uses biased blocks, established at
  ingestion from the documentation (Behavior → 2, step 3). If it does not, none of
  `skills/ibl-analyze/references/prior_and_block_semantics.md` or the
  `probabilityLeft` guidance applies, and the package carries no
  `probabilityLeft` column. Stating this is what keeps routing the pilot to
  `ibl-analyze` unchanged from carrying a known misleading reference.

It must also state which BWM-specific surfaces do not apply, covering audit items
1–7:

- routing (items 1–5) — `skills/ibl-analyze/SKILL.md` default policy #7
  ("Prefer local BWM tables and shards...", `skills/ibl-analyze/SKILL.md:33`);
  `references/operators.md` Operator Map, BWM Loading Route and General Rules;
  `references/visual_latency.md` inputs, whose fallback routes into the BWM release
  helper; `references/bwm_analysis_patterns.md`, including its BWM trial mask
  instruction.
- inclusion and QC (items 6–7) — there is no `bwm_include` trial mask, so the
  inclusion rule is whatever the package declares; and canonical release QC may not
  exist, so BWM's `label >= 1.0` must not be borrowed silently.

### 4. Spike shard writing
`spikepack.write_blosc` is the only shard writer for ingested datasets.
`extra_meta` carries, at minimum: `dataset_name`, `dataset_version`, `shard_key`,
`shard_id`, `session_id`, `subject_id`, `source_selection_rule`, `time_base`,
`n_spikes`, `n_units`, `cluster_encoding`, `time_encoding`, `compression`.

Origins are tick-aligned. A float cannot be an exact multiple of 100 µs, so this is
done by construction: before calling `write_blosc` the ingestion writer snaps every
spike time to the grid,

```python
q = quantization_us
times_seconds = np.rint(times_seconds * 1e6 / q) * q / 1e6
```

so each time, including the first, is the float that `ticks * q / 1e6` produces. The
`time_origin_ticks` and `time_origin_seconds` decoders then agree exactly. Snapping is
at most half a tick per spike — the same bound the encoder already applies — and is
recorded under `provenance.yaml` `conversion.lossy`.

### 5. Shared spike reader
`load_spike_shard` moves from `ibl_ai_agent/datasets/bwm_ephys.py` to
`ibl_ai_agent/datasets/spike_store.py` and is re-exported from `bwm_ephys`.

It continues to use `time_origin_ticks`, unchanged. It reads both origin layouts
already present or produced:
- offset in `delta[0]` with `time_origin_ticks == 0` — 696 of the 699 shipped
  `bwm_ephys/1.2.1` shards;
- `delta[0] == 0` with the offset in `time_origin_ticks` — written by spikepack **and
  by the current in-repo encoder** (`_encode_spike_times_dataset`,
  `bwm_ephys.py:1534`), and present in the three shipped shards with non-zero
  origins.

The layout difference is between the shipped release and current code, not between
this repo and spikepack.

`spike_store.py` imports `compress_array` / `read_array_directory` from
`bwm_shared`; those functions do not move.

### 6. Dataset discovery and routing
`AGENTS.md` gains:
- a dataset-discovery step that enumerates datasets configured in
  `data_locations.local.yaml` and reads each package's `README.md` summary;
- a Required Load Packet for **analysing** an ingested dataset:
  `skills/ibl-analyze/SKILL.md` — the analysis guardrails apply to every dataset,
  not only BWM — together with the package's `README.md`, `experiment.md`,
  `modalities.md`, `scientific-context.md` when present, and
  `ingestion/open-questions.md`.
  `skills/ibl-analyze/references/bwm_analysis_patterns.md` is **not** in this
  packet; it stays conditional on a BWM question.
- a separate Required Load Packet for **ingesting** a dataset:
  `skills/ibl-ingest/SKILL.md`. `ibl-ingest` covers ingestion only and is not
  loaded for questions that analyse a package.

The existing "Brain Wide Map question" packet at `AGENTS.md:70-73` stays first and
its three entries are unchanged:
`skills/ibl-load/references/bwm_runtime_policy.md`,
`skills/ibl-load/references/bwm_ephys_spike_example.md`,
`skills/ibl-analyze/references/bwm_analysis_patterns.md`.

### 7. Generic events mapping
Generic `events` contract: `session_id`, `event_id`, `event_name`, `event_time`,
nullable `trial_id`, nullable `event_value`, plus declared extra columns.

BWM's `metadata/events.parquet` has columns `eid`, `trial_id`, `event_id`,
`subject`, `date`, `session_number`, `lab`, `event_name`, `event_time`. It differs
only in the session key. The mapping is held reader-side: `dataset_kind: bwm` uses
a built-in column map `session_id <- eid`; ingested packages declare `column_map`
in their own `schema.yaml`. No BWM file is rewritten.

### 8. Pilot routing
Aging and autism use the same IBL task, so questions analysing either package load
`skills/ibl-analyze/` as it stands, through the analysis packet in 6. That skill is
not edited by this change. `skills/ibl-ingest/` builds the two packages and is not
loaded when analysing them.

The audit of BWM-specific assumptions to watch during the pilot is recorded in
`ingestion-notes.md`. The parts of it that must be written into each package's
`scientific-context.md` are listed in 3.

### Acceptance criteria
1. The `load_spike_shard` move to `ibl_ai_agent/datasets/spike_store.py` is a pure
   move — import path preserved via re-export from `bwm_ephys`, diff shows no logic
   change, existing BWM tests pass.
2. A test asserts that the "Brain Wide Map question" block in `AGENTS.md` is
   byte-identical to its text before this change, that it is still the first
   dataset-specific packet under "Required Load Packets", and that the new discovery
   step and packets are additive (no existing packet line removed or edited).
   Routing is prose interpreted by the model, so which files a BWM question loads
   cannot be unit-tested directly; this is the testable proxy.
3. Decoded spike times for all 699 BWM shards, including the three with non-zero
   non-tick-aligned origins
   (`11a5a93e-58a9-4ed0-995e-52279ec16b98`,
   `50f1512d-dd41-4a0c-b3ab-b0564f0424d7`,
   `5a34d971-1cb3-4f0e-8dfe-e51e2313a668`), are identical before and after.
4. The ingestion writer emits tick-aligned spike origins.
5. Round trip: a shard written by `spikepack.write_blosc` with a tick-aligned
   origin — `times_seconds` all exact multiples of `quantization_us` — decodes
   through `load_spike_shard` with **exact** equality (`==`, not `allclose`) to the
   inputs: `spike_times_seconds` to `times_seconds`, `spike_clusters` to `labels`,
   `cluster_ids` to `cluster_ids`. The inputs are synthetic, built on the grid as in
   Behavior → 4; real spike times only meet this after snapping.

6. The BWM builder's `trials` and `events` output is byte-identical before and
   after the `_build_trials` / `_build_events` generalisation. This is the test the
   change is guarded by, and it is what "BWM behaves exactly as before" means here
   — additive keyword-only parameters whose defaults reproduce current behaviour are
   permitted; a change in output is not.
7. `_build_trials` called with `roster=None` on a trials frame lacking
   `probabilityLeft` and `bwm_include` returns without raising, omits those columns
   and the roster-derived columns, and leaves the order of the columns it does emit
   in canonical order. The same call on a frame lacking a required column raises.
8. `_build_events` called with `event_time_dtype=np.float64` returns an
   `event_time` column of dtype float64; called without it, float32.
9. `one_trials.py` returns one concatenated frame with an `eid` column over a
   multi-session input, against a stubbed ONE.

Criterion 3 requires a baseline captured before the move: per-shard SHA-256 of the
decoded `spike_times_seconds` float64 buffer, stored as a test fixture. The full
699-shard run reads ~6 GB and is opt-in, marked to require a configured local
`bwm_ephys`; the three named pids run whenever that dataset is present.

Criteria 4 and 5 require `spikepack`, so their tests gate on
`pytest.importorskip("spikepack")` — skipped on Python 3.10 and wherever the
`ingest` extra is not installed. They are exercised in CI by a second job on 3.12
(Change surface). Criteria 6–9 need neither `spikepack` nor ONE and run everywhere.

### Change surface

New:
- `specs/data-ingestion.md` (this file)
- `skills/ibl-ingest/SKILL.md` — v0, to be revised from the pilot's ingestion notes
- `ibl_ai_agent/datasets/spike_store.py`
- `ibl_ai_agent/datasets/one_trials.py` — per-session ONE trials loader
- `tests/test_spike_store.py` — criteria 1 and 3
- `tests/test_agents_routing.py` — criterion 2
- `tests/test_ingest_package.py` — criteria 4 and 5, package contract validation
- `tests/test_bwm_builder_identity.py` — criteria 6, 7 and 8
- `tests/test_one_trials.py` — criterion 9
- `tests/fixtures/bwm_shard_decoded_hashes.json` — criterion 3 baseline

Modified:
- `ibl_ai_agent/datasets/bwm_ephys.py` — two changes. Remove the
  `load_spike_shard` body at L1586 and re-export from `spike_store`; internal
  callers at L1173 and L2077 keep working via the re-export or a direct import. And
  give `_build_events` (L907) keyword-only `event_time_dtype` and
  session-key/carried-column control.
- `AGENTS.md` — additive discovery step and non-BWM load packet
- `pyproject.toml` — `ingest` optional-dependency extra pinning `spikepack` by SHA
  and carrying the environment marker `python_version >= '3.11'`
- `.github/workflows/ci.yaml` — second job on Python 3.12 running
  `uv sync --extra dev --extra ingest`, so the tests gated on `spikepack` are
  exercised somewhere. The existing 3.10 job is unchanged.
- `ibl_ai_agent/datasets/bwm_simple.py` — `_build_trials` accepts a DataFrame or a
  path, `roster` optional, required/optional column split
- `project-structure.md` — `contract_version`, `task` and `task_protocol` in the
  `schema.yaml` contract; the BWM constraint restated as byte-identical output and
  extended with the `_build_trials` gate and column lists; its open list emptied,
  with local dataset revisions and the timeseries container format moved to deferred
  and the size and protocol questions moved to settled-at-ingestion
- `ingestion-notes.md` — open questions closed
- `docs/data_locations.md` — registering an ingested dataset
- `docs/skills.md` — list `skills/ibl-ingest/`
- `CHANGELOG.md`

Read by the move, not modified:
- `ibl_ai_agent/datasets/bwm_ephys_passive.py:561` calls
  `bwm_ephys.load_spike_shard`; preserved by the re-export.
- `tests/test_bwm_ephys_dataset.py:343` calls `bwm_ephys.load_spike_shard`;
  preserved by the re-export.
- `skills/ibl-load/references/bwm_ephys_spike_example.md:15`,
  `skills/ibl-load/references/repeated_site_pids.md:100`,
  `skills/ibl-load/references/bwm_runtime_policy.md:87`,
  `skills/ibl-analyze/references/visual_latency.md:8` all document the import path
  `ibl_ai_agent.datasets.bwm_ephys.load_spike_shard`; preserved by the re-export,
  so none of these skill files change.

Explicitly unchanged:
- `pyproject.toml` `requires-python = ">=3.10"` (L10) and `[tool.ruff]
  target-version = "py310"` (L68); the existing CI job's `python-version: "3.10"`
  (`.github/workflows/ci.yaml:24`). The 3.11 floor applies to the `ingest` extra
  only.
- `ibl_ai_agent/data_locations.py`. `resolve_dataset_dir` only calls
  `_missing_bwm_dataset_message` when `name in BWM_DATASET_DEFAULTS`; an unconfigured
  non-BWM dataset already gets a generic "not configured" error, not a BWM download
  offer. No change needed.
- all files under `reports/datasets/bwm_ephys/` and `reports/datasets/bwm_behavior/`
- `ibl_ai_agent/datasets/bwm_ephys.py` spike writer:
  `_encode_spike_times_dataset` (L1534), `SpikeShardWriter` (L409)
- `skills/ibl-analyze/` — every file
- `docs/bwm/` — every file

## Out of scope
- Lifting the dataset-independent semantic core out of `skills/ibl-analyze/`.
  Target design and seam recorded in `ingestion-notes.md`; deferred because it
  edits the skill governing all BWM analysis.
- Retiring `_encode_spike_times_dataset` / `SpikeShardWriter` in favour of
  `spikepack`. Deferred to the next `bwm_ephys` version bump.
- Converting LFP or video to shards. Referenced in place for now.
- `validate-dataset` CLI command. The minimum-viable-package rules are enforced by
  the skill in this iteration.
- NWB/DANDI reader, per-lab format readers, two-photon reader, tracking reader,
  generic feature builders, timeseries container format. All recorded as
  implementation gaps in `ingestion-notes.md`.
- Any change to BWM data, schemas, builder, or analysis guidance.
- Retrofitting `source_selection_rule` into existing BWM shards.
- Retrofitting float64 `event_time` into BWM.
- Reading NWB directly without conversion (e.g. with `pynapple`), which would avoid
  writing shards at all. Deferred to a later, separate test; not part of this pilot.
- Managing multiple dataset versions on local disk — which versions are kept, how
  superseded ones are removed, and whether a rebuild may overwrite. Deferred: the
  pilot writes one version per package, and duplicate copies costing disk space is a
  problem that already exists independently of this change.
- Codec and chunking for the `timeseries` store kind. Deferred: the store kind is
  declared per store, so settling it later is not a layout change, and the pilot
  references LFP and video in place rather than writing a timeseries store.
  Recorded as implementation gap I5 in `ingestion-notes.md`.
- Raising the repo's Python floor, or publishing `spikepack` to PyPI. The `ingest`
  extra's environment marker confines the 3.11 requirement to ingestion; a PyPI
  release is to be requested from Olivier separately, and would also remove the
  git-only install.

## Decisions

- **Ingested datasets are dataset packages under the existing `datasets:` contract,
  not a new top-level concept.** User decision. `resolve_dataset_dir` is already
  dataset-name generic and the `schema.yaml` / `provenance.yaml` / `manifest.json`
  triple is the right shape; a parallel mechanism would mean two discovery paths
  for structurally identical things.
- **Metadata tables are materialised; spikes are converted; LFP and video are
  referenced in place.** User decision: shard conversion of spikes was the agreed
  end state and the raw aging data is too large uncompressed.
- **`spikepack` is the shard writer; no `spike_shards.py` is added.** User
  decision, after verifying spikepack was extracted from this repo's builder and
  writes the same format.
- **`load_spike_shard` moves; the BWM writer does not.** User decision, taking the
  fallback option to avoid touching the BWM builder in this piece of work.
- **The reader keeps using `time_origin_ticks`; ingestion writes tick-aligned
  origins instead.** Reversal of an earlier suggestion. Preferring
  `time_origin_seconds` is not a no-op on BWM: of 699 shards, 696 have
  `(time_origin_seconds, time_origin_ticks) == (0.0, 0)`, but three have
  non-tick-aligned negative origins, and the change would shift every spike time on
  those probes by 41.7, 25.9 and 49.4 µs respectively — below the 100 µs
  quantization, but a silent change to existing results. Evidence in
  `ingestion-notes.md`.
- **The generic `events` mapping is held reader-side.** User decision: define the
  generic table so BWM's conforms or maps via a view; do not change BWM's.
- **`age_at_session_days` is on `sessions`, not `subjects`.** Age varies by session
  and is the aging dataset's primary scientific variable.
- **Units are required for every column of every declared table and store**, not
  only required tables. User decision. `features/`, conditional tables and
  timeseries stores are where imaging and LFP data land; the narrower rule would
  have held for the pilot and failed generally.
- **Eight structural fixes** — timeseries store kind, `spikes` as discrete event
  times only, modality-conditional required tables, per-table/store `time_base`,
  `reference_frames`, `epoch_set`, machine-readable `design` block,
  `source_selection_rule` — come from stress-testing the layout against free
  exploration, two-photon imaging, NWB/DANDI, a README-only lab format, and the
  IBL aging and autism datasets. Recorded with their failing case in
  `ingestion-notes.md`.
- **The pilot routes to `skills/ibl-analyze/` unchanged.** User decision: aging and
  autism use the same IBL task.
- **Analysis of an ingested dataset loads the `ibl-analyze` guardrails; `ibl-ingest`
  is for ingestion only.** User decision, correcting an earlier draft in which the
  non-BWM packet routed analysis questions to `ibl-ingest`. The guardrails —
  metric classification, shape-before-scalar, statistical unit, ambiguity policy —
  are dataset-independent, so an ingested dataset needs them as much as BWM does;
  the ingestion skill has nothing to say about analysing a package once written.
- **`scientific-context.md` is required for the IBL aging and autism packages.**
  User decision. It is where the between-subject design and the recording-quality
  confound get stated, and those are exactly the gaps the audit found in
  `ibl-analyze` (items 9–11). Since the pilot routes to that skill unchanged, the
  package file is the only place the correction can live. The general contract in
  `project-structure.md` keeps the file optional.
- **The aging and autism `trials` tables reuse the `bwm_behavior` trials
  extraction, by generalising `_build_trials` and `_build_events` rather than
  writing parallel functions.** User decision. Same IBL task and the same upstream
  trial columns, so a second extractor would be duplicated logic that can drift —
  and the thing most likely to drift, which columns a trials table has, is exactly
  what a parallel builder would duplicate. The alternative considered was sharing
  `_build_events` only and lifting the trial column list to a constant for a
  separate ingestion-side builder; rejected for that reason.
- **The BWM constraint is "output is byte-identical", not "no BWM file is
  edited".** User decision, loosening the constraint as first written. Its purpose
  is unchanged BWM results, which a byte-identity test (acceptance criterion 6)
  enforces directly; the stricter phrasing also forbade strictly additive
  keyword-only parameters that cost nothing and cannot change existing behaviour.
- **The generalisation is by keyword-only parameters whose defaults reproduce
  current behaviour**, not by new call sites or wrappers: `_build_trials` takes a
  DataFrame or a path with `roster` optional and a required/optional column split,
  `_build_events` takes `event_time_dtype` defaulting to `np.float32`. BWM's call
  sites are unchanged.
- **Reuse of `_build_trials` is gated on the package declaring the IBL task.** User
  decision. The function encodes the IBL trial structure, so applying it to a
  dataset with a different trial structure would produce a table whose columns mean
  something other than what they are named. `task: ibl_choice_world` in
  `schema.yaml` is the gate; a generic trials builder for other tasks is out of
  scope.
- **The required set is the minimum that defines an IBL trial; everything else is
  optional and a missing optional column is skipped, not an error.** User decision.
  Required: `eid`, `intervals_0`, `intervals_1`, `stimOn_times`, `contrastLeft`,
  `contrastRight`, `choice`, `feedbackType` — extent, stimulus, response, outcome.
  A trials table missing any of these is not an IBL trials table, so failing is
  right. Everything else, `probabilityLeft` and `bwm_include` included, varies by
  rig, protocol and release, so an error there would reject valid data; the skip is
  recorded in `ingestion/ingestion-log.md` and `ingestion/open-questions.md` so it
  is visible to whoever later analyses the package rather than silent.
- **`feedbackType` is required, `feedback_times` is not.** What happened defines the
  trial; when it happened is an event time like the others, and `_build_events`
  already skips absent event source columns
  (`ibl_ai_agent/datasets/bwm_ephys.py:911-913`). Applying the same rule to the
  trials table keeps the two consistent.
- **Emitted column order stays canonical, with absent optional columns dropped in
  place.** Required for BWM byte-identity: BWM supplies every column in both groups,
  so grouping required before optional would reorder its output even though the
  contents matched.
- **The per-session ONE trials loader lives in the repo, at
  `ibl_ai_agent/datasets/one_trials.py`, not in the generated
  `ingestion/convert.py`.** User decision. Both pilot packages need identical
  behaviour from it and it needs a test, whereas `convert.py` is a per-package
  artifact that varies by dataset. `convert.py` calls it, which also keeps
  `convert.py` an honest record of the conversion.
- **Ingestion measures before it converts in bulk.** User decision, which is what
  closed the raw-data-size question rather than answering it: the size is measured
  on the server from raw size per session and shards written for 2–3 sessions, and
  the full run is estimated from those and approved before it starts. This
  instantiates the existing "Start small" policy in `AGENTS.md`; it is not a new
  rule, and it means the pilot does not need the size known in advance.
- **Whether the protocol uses biased blocks is settled at ingestion time**, from
  the paper, README or metadata supplied to the agent, not in this spec. User
  decision. It is exactly the kind of fact the step-3 documentation checklist
  exists to elicit, so it needs no separate mechanism; it gates whether
  `probabilityLeft` is written and what `scientific-context.md` says about
  `prior_and_block_semantics.md`.
- **The `ingest` extra requires Python ≥ 3.11 through an environment marker; the
  repo and CI stay on 3.10.** User decision, choosing the least disruptive option
  over raising the repo floor. Ingestion tests gate on
  `pytest.importorskip("spikepack")`, which skips both on 3.10 and where the extra
  is not installed, and a second CI job on 3.12 keeps those tests exercised. A
  `spikepack` PyPI release supporting 3.10 is to be requested separately.
- **`contract_version: 1` in `schema.yaml`, beside the existing
  `schema_version`.** User decision. `schema_version` is already per-dataset and
  inconsistent across datasets — `bwm_ephys` declares `1`
  (`ibl_ai_agent/datasets/bwm_ephys.py:24`), `bwm_behavior` declares `2`
  (`ibl_ai_agent/datasets/bwm_behavior.py:30`) — so it means "version of this
  dataset's own layout" and cannot also carry the generic contract's version.
  Adding a key leaves both meanings unambiguous and changes no existing file.
- **`skills/ibl-ingest/SKILL.md` ships as v0.** User decision. It is written from
  this spec before the pilot has run, so the pilot's `ingestion-log.md` and
  `open-questions.md` are the evidence for its first revision.

## Open questions

None.

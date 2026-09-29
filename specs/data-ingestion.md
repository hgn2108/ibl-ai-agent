# Spec: Generic data ingestion and standardised dataset packages

## Status
Draft
2026-09-29

## Problem
The agent can only analyse the IBL Brain Wide Map, because BWM's task description,
scientific context and data layout are hard-coded across `AGENTS.md`, `skills/` and
`docs/bwm/`. Analysing the IBL aging and autism datasets — and later any lab's
neurophysiology data, including experiments that are not trial-based — requires a
repeatable way to turn a documented raw dataset into a self-describing **dataset
package** that a later agent can analyse without re-reading the raw source. This
spec covers the ingestion skill that writes such packages, the package contract
itself, and the minimum repo changes needed to read them, while leaving BWM's data,
schemas, builder and analysis guidance untouched.

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
  `stores:` shape the package contract extends.

### External dependency
- `spikepack`, `int-brain-lab/spikepack`, MIT. Version `0.1.0` at commit
  `30ab06ff7794d89cab17cb54338db869ad90d036`. Public API used: `write_blosc`.
- `write_blosc(path, *, times_seconds, labels=None, cluster_ids=None,
  quantization_us=100, extra_meta=None) -> int`.
- Package dependencies: `numpy`, `numcodecs`. `requires-python = ">=3.11"`.
- Not on PyPI: `https://pypi.org/pypi/spikepack/json` returns 404 for both
  `spikepack` and `spike-pack` as of 2026-09-29. Install is from git.

## Outputs

### A dataset package
Written to `<dataset_root>/<dataset_name>/<version>/`, registered in
`data_locations.local.yaml` under `datasets:`. Contents as defined in
`project-structure.md`:

- `README.md`, `experiment.md`, `modalities.md`, optional `scientific-context.md`
- `schema.yaml`, `provenance.yaml`, `manifest.json`, `SUMMARY.md`
- `metadata/` — core tables `subjects`, `sessions`, `recordings`, `events`,
  `epochs`; conditional tables `units`, `channels`, `trials`
- `features/` — optional
- stores of kind `spike_shards`, `timeseries`, or `referenced_in_place`
- `ingestion/convert.py`, `ingestion/ingestion-log.md`,
  `ingestion/open-questions.md`

Constraints:
- `events.event_time` is float64 seconds in the table's declared `time_base`.
- Every column of every declared table and store declares `units`. `a.u.` and
  `dimensionless` are valid.
- Every table and store names a `time_base` declared in `time_bases:`.
- Spike shards are written by `spikepack.write_blosc` with tick-aligned origins.

### Repo changes
Enumerated in Behavior → Change surface.

## Behavior

### 1. Package contract
`project-structure.md` is the normative description of the package layout,
`schema.yaml` and `provenance.yaml` contracts, core and conditional tables, store
kinds, minimum viable package, and versioning. This spec does not restate it.

### 2. Ingestion skill
New skill `skills/ibl-ingest/SKILL.md`. Steps:

1. Read the raw dataset and its documentation.
2. Draft `README.md`, `experiment.md`, `modalities.md` from what the documentation
   states.
3. Identify blocking gaps. Ask the user. Do not infer.
4. Write `schema.yaml` — tables, stores, `time_bases`, `reference_frames`,
   `design`, per-column `units`.
5. Materialise the metadata tables as parquet.
6. Convert spikes to shards via `spikepack.write_blosc`.
7. Reference LFP and video in place, recording re-resolution keys.
8. Write `provenance.yaml`, `manifest.json`, `SUMMARY.md`,
   `ingestion/convert.py`, `ingestion/ingestion-log.md`,
   `ingestion/open-questions.md`.
9. Register the package in `data_locations.local.yaml`.

### 3. Minimum viable package
Ingestion stops and asks rather than shipping without: `dataset_name`,
`dataset_version`, the `README.md` summary, a declared time base, units for every
column of every declared table and store, `subjects` and `sessions`,
`provenance.source`, and for every declared store either materialised data or a
re-resolvable reference.

Ingestion may ship, recording an entry in `ingestion/open-questions.md`, without:
`scientific-context.md`, `features/`, per-column prose beyond units, exact
conversion detail for upstream-derived fields, optional modalities.

### 4. Spike shard writing
`spikepack.write_blosc` is the only shard writer for ingested datasets.
`extra_meta` carries, at minimum: `dataset_name`, `dataset_version`, `shard_key`,
`shard_id`, `session_id`, `subject_id`, `source_selection_rule`, `time_base`,
`n_spikes`, `n_units`, `cluster_encoding`, `time_encoding`, `compression`.

Origins are tick-aligned: the ingestion writer passes `times_seconds` whose first
element is an exact multiple of `quantization_us`, so
`time_origin_seconds == time_origin_ticks * quantization_us / 1e6` exactly, and the
`time_origin_ticks` and `time_origin_seconds` decoders agree.

### 5. Shared spike reader
`load_spike_shard` moves from `ibl_ai_agent/datasets/bwm_ephys.py` to
`ibl_ai_agent/datasets/spike_store.py` and is re-exported from `bwm_ephys`.

It continues to use `time_origin_ticks`, unchanged. It reads both origin layouts:
BWM's offset-in-`delta[0]` with `time_origin_ticks == 0`, and spikepack's
`delta[0] == 0` with the offset in `time_origin_ticks`.

`spike_store.py` imports `compress_array` / `read_array_directory` from
`bwm_shared`; those functions do not move.

### 6. Dataset discovery and routing
`AGENTS.md` gains:
- a dataset-discovery step that enumerates datasets configured in
  `data_locations.local.yaml` and reads each package's `README.md` summary;
- a Required Load Packet for non-BWM dataset questions, routing to
  `skills/ibl-ingest/SKILL.md` and the package's `README.md`, `experiment.md`,
  `modalities.md`, `ingestion/open-questions.md`.

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
Aging and autism use the same IBL task and route to `skills/ibl-analyze/` as it
stands. That skill is not edited by this change. The audit of BWM-specific
assumptions to watch during the pilot is recorded in `ingestion-notes.md`.

### Acceptance criteria
1. The `load_spike_shard` move to `ibl_ai_agent/datasets/spike_store.py` is a pure
   move — import path preserved via re-export from `bwm_ephys`, diff shows no logic
   change, existing BWM tests pass.
2. A test asserts that a BWM question loads exactly the same files as before the
   `AGENTS.md` routing/discovery change.
3. Decoded spike times for all 699 BWM shards, including the three with non-zero
   non-tick-aligned origins
   (`11a5a93e-58a9-4ed0-995e-52279ec16b98`,
   `50f1512d-dd41-4a0c-b3ab-b0564f0424d7`,
   `5a34d971-1cb3-4f0e-8dfe-e51e2313a668`), are identical before and after.
4. The ingestion writer emits tick-aligned spike origins.

Criterion 3 requires a baseline captured before the move: per-shard SHA-256 of the
decoded `spike_times_seconds` float64 buffer, stored as a test fixture. The full
699-shard run reads ~6 GB and is opt-in, marked to require a configured local
`bwm_ephys`; the three named pids run whenever that dataset is present.

### Change surface

New:
- `specs/data-ingestion.md` (this file)
- `skills/ibl-ingest/SKILL.md`
- `ibl_ai_agent/datasets/spike_store.py`
- `tests/test_spike_store.py` — criteria 1 and 3
- `tests/test_agents_routing.py` — criterion 2
- `tests/test_ingest_package.py` — criterion 4, package contract validation
- `tests/fixtures/bwm_shard_decoded_hashes.json` — criterion 3 baseline

Modified:
- `ibl_ai_agent/datasets/bwm_ephys.py` — remove the `load_spike_shard` body at
  L1586, re-export from `spike_store`. Internal callers at L1173 and L2077 keep
  working via the re-export or a direct import.
- `AGENTS.md` — additive discovery step and non-BWM load packet
- `pyproject.toml` — `ingest` optional-dependency extra pinning `spikepack` by SHA
- `ibl_ai_agent/data_locations.py` — non-BWM branch in
  `_missing_bwm_dataset_message`, so an unconfigured ingested dataset does not
  produce a BWM download offer
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

## Open questions

1. **`schema_version` for ingested packages.** `schema_version` is already
   per-dataset and inconsistent across existing datasets — `bwm_ephys` declares
   `1` (`ibl_ai_agent/datasets/bwm_ephys.py:24`), `bwm_behavior` declares `2`
   (`ibl_ai_agent/datasets/bwm_behavior.py:30`). It therefore means "version of
   this dataset's own layout", not a contract version, and the generic package
   contract needs a separate key. Name and starting value not decided.
2. **`spikepack` requires Python ≥ 3.11; this repo declares
   `requires-python = ">=3.10"`** (`pyproject.toml`). The `ingest` extra would be
   uninstallable on 3.10. Unresolved: raise the repo floor, constrain the extra, or
   vendor the codec.
3. **Raw data size** for the aging and autism datasets. Determines whether shard
   conversion is feasible in the pilot. Pending from the user.
4. **Do the aging and autism protocols use biased blocks?** Determines whether
   `skills/ibl-analyze/references/prior_and_block_semantics.md` and all
   `probabilityLeft` guidance apply. If they do not, routing the pilot to
   `ibl-analyze` unchanged carries a known misleading reference.
5. **Timeseries container format** — codec and chunking for the `timeseries` store
   kind. Recorded as implementation gap I5; the store kind is declared per store so
   this is not a layout change, but no store can be written until it is chosen.

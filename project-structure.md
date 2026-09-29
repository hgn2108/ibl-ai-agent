# Ingested dataset package structure

Standardised on-disk structure written by the data-ingestion skill, so that an
agent can analyse a dataset it has never seen without re-reading the raw source.

Status: design, agreed. Implementation not started. Working decisions and their
evidence are in `ingestion-notes.md`.

## What a package is

A **dataset package** is one dataset, at one version, in one directory: its prose
description, its machine-readable schema, its provenance, its metadata tables, and
its bulk signal stores.

It is not a "project" in this repo's existing sense. `projects/<project_slug>/`
continues to mean an *analysis* project (`question.md`, `TODO.md`,
`exploratory-analyses/`, …) as defined in `AGENTS.md`. Dataset packages are data,
live outside the checkout, and are registered in `data_locations.local.yaml`
alongside `bwm_ephys` and `bwm_behavior`.

Prose lives **inside the package**, not in this repo. BWM's prose is in
`docs/bwm/` and `skills/` for historical reasons and stays there; an arbitrary
lab's dataset has no repo to keep its documentation in, so the package must carry
its own.

## Registration

```yaml
# data_locations.local.yaml
datasets:
  ibl_aging:
    root: /path/to/datasets/ibl_aging
    preferred_version: latest
```

`ibl_ai_agent.data_locations.resolve_dataset_dir()` is already dataset-name
generic and needs no change beyond a non-BWM branch in the "dataset missing"
error message (which currently offers a BWM download).

## Directory tree

```
<dataset_root>/<dataset_name>/<version>/
├── README.md                  # one-paragraph summary; the only file needed to judge relevance
├── experiment.md              # methods section: what was done, portable and lab-neutral
├── scientific-context.md      # optional: interpretation, hypotheses, confounds, papers
├── modalities.md              # per modality: instrument, sampling, units, timing, coverage, QC
├── schema.yaml                # machine-readable contract: tables, stores, clocks, frames, design
├── provenance.yaml            # where it came from and what was done to it
├── manifest.json              # file inventory with sizes and hashes
├── SUMMARY.md                 # generated counts
├── metadata/
│   ├── subjects.parquet       # core
│   ├── sessions.parquet       # core
│   ├── recordings.parquet     # core
│   ├── events.parquet         # core (may be empty)
│   ├── epochs.parquet         # core (may be empty)
│   ├── units.parquet          # conditional: discrete sorted or segmented sources
│   ├── channels.parquet       # conditional: electrode-based recordings
│   └── trials.parquet         # conditional: trial-based experiments
├── features/                  # optional derived summaries
├── spikes/<shard_id>/         # store: discrete spike times, spikepack Blosc shards
├── <timeseries stores>/       # store: continuous sampled signals
└── ingestion/
    ├── convert.py             # the conversion script(s)
    ├── ingestion-log.md       # what was done, what was inferred, what was asked
    └── open-questions.md      # unresolved items an analysis agent must know about
```

## Files

### `README.md`
Fixed headings: `Summary` | `Scope` | `When to use` | `When not to use`.
`Summary` is one paragraph: species, subject and session counts, modalities,
scientific aim. This is what the dataset-discovery step reads across all
configured datasets to choose one, so it must be sufficient on its own.

### `experiment.md`
A methods section. Portable and lab-neutral: it describes the experiment, not IBL's
interpretation of it. Fixed headings:
`Subjects` | `Surgery` | `Apparatus` | `Protocol` | `Design and factors` |
`Trial structure` | `Session schedule` | `Training history`.
Headings that do not apply are kept and marked not applicable.

`Design and factors` is required and mirrors the machine-readable `design:` block
in `schema.yaml`: which factors the experiment manipulates or measures, at what
grain, and what comparison it was built for.

### `scientific-context.md`
Optional, non-blocking. Dataset-specific interpretation, hypotheses, known
confounds, associated papers. Kept separate from `experiment.md` so the methods
stay reusable, and separate from `skills/` so IBL-wide scientific context is not
duplicated per dataset.

### `modalities.md`
One section per recording modality, fixed headings:
`Instrument` | `Sampling` | `Units` | `Preprocessing` | `Time base` | `Coverage` | `QC`.
Prose counterpart to the `stores:` and `time_bases:` blocks in `schema.yaml`.

### `schema.yaml`
The machine-readable contract. Extends the existing `bwm_ephys` schema shape with
per-column units, explicit clocks, spatial frames, and experimental design.

```yaml
dataset_name: ibl_aging
dataset_version: 1.0.0
schema_version: 2
dataset_kind: ingested            # `bwm` for the existing BWM datasets

time_bases:                       # several allowed; each store and table names one
  session_clock:
    origin: session_start
    clock: daq
    aligned_to: null
  imaging_clock:
    origin: first_frame
    clock: scanner
    aligned_to: session_clock
    method: ttl_pulse_regression

reference_frames:                 # non-time coordinate systems
  arena:
    origin: arena_centre
    axes: [x, y]
    units: cm

design:                           # what the experiment manipulates or measures
  factors:
    age:      {grain: between_session, type: continuous,  units: days}
    genotype: {grain: between_subject, type: categorical, levels: [wt, ko]}
  intended_comparison: >
    Neural and behavioural differences across age, within genotype.

tables:
  sessions:
    path: metadata/sessions.parquet
    primary_key: [session_id]
    time_base: session_clock
    columns:
      session_id:         {dtype: str,     units: null,    description: ...}
      age_at_session_days: {dtype: float64, units: days,   description: ...}
  epochs:
    path: metadata/epochs.parquet
    primary_key: [session_id, epoch_set, epoch_id]
    time_base: session_clock
    columns: {...}
  # column_map: {session_id: eid}   # only where source column names differ

stores:
  spikes:
    kind: spike_shards
    path: spikes
    shard_key: recording_id
    container_format: blosc_file_shards
    shard_layout: <recording_id>/meta.json + <recording_id>/*.blosc
    arrays: [spike_times_delta_ticks, spike_clusters, cluster_ids, cluster_spike_counts]
    written_by: spikepack==<version>
    quantization_us: 100
    time_base: session_clock
    units: seconds
  fluorescence:
    kind: timeseries
    path: fluorescence
    sources: rois
    rate_hz: 30.0
    t0: 0.0
    units: a.u.
    time_base: imaging_clock
    container_format: <chosen per store>
  lfp:
    kind: referenced_in_place
    reader: spikeglx
    units: volts
    time_base: session_clock
    resolve: {one_eid: ..., dataset: ..., collection: ..., revision: ...}
```

### `provenance.yaml`
Where the data came from and what was done to it.

```yaml
source:
  url: ...
  doi: ...
  lab: ...
  contact: ...
  version: ...              # the UPSTREAM version, independent of the package version
  access: public | restricted
conversion:
  steps: [...]              # ordered, human-readable
  tools: {spikepack: ..., ibl-ai-agent: ...}
  lossy: [...]              # anything not reversible, e.g. 100 us spike quantization
  dropped: [...]            # anything in the source not carried into the package
source_selection_rule: ...  # which units/ROIs were kept, and why
ingested_at: ...
ingested_by: ...
```

`source_selection_rule` is also echoed into each spike shard's `meta.json`, so a
shard is self-describing about whether it holds all sources or a QC subset. Not
retrofitted to BWM shards.

### `manifest.json`, `SUMMARY.md`
As for `bwm_ephys`: file inventory with sizes and hashes; generated counts of
subjects, sessions, recordings, sources and events.

### `metadata/` — core tables

| Table | Grain | Notes |
| --- | --- | --- |
| `subjects` | one row per subject | `subject_id`, `line`, `genotype`, `sex`, `dob`, `cohort` |
| `sessions` | one row per session | `session_id`, `subject_id`, `date`, `age_at_session_days`, `protocol`, `lab`, `rig`, `duration` |
| `recordings` | one row per recording device instance | `recording_id`, `session_id`, device, target, sync source |
| `events` | one row per named instant | `session_id`, `event_id`, `event_name`, `event_time` (float64 s), nullable `trial_id`, nullable `event_value`, plus declared extra columns |
| `epochs` | one row per labelled interval | `session_id`, `epoch_set`, `epoch_id`, `label`, `start_time`, `stop_time` |

`events` and `epochs` are required to exist and may be empty.

`age_at_session_days` is on `sessions`, not `subjects`: age varies by session and
is the primary scientific variable for an aging dataset.

`epoch_set` is a labeling namespace, so independent and overlapping labelings of
the same session — locomotion state, zone occupancy, sleep stage, drug on/off —
coexist without ambiguity.

Together these carry non-trial-based behaviour without schema change: named
instants with an optional scalar value and declared extra columns, and named
intervals within a namespace.

### `metadata/` — conditional tables

- `units` — when discrete sources are sorted or segmented (spike-sorted units,
  imaging ROIs). Columns are dataset-declared.
- `channels` — electrode-based recordings only.
- `trials` — trial-based experiments only.

### `features/`
Optional derived summaries. Where a dataset wants BWM-compatible analysis
patterns to transfer, these should use BWM's `unit_features` /
`event_response_features` schema.

### Stores

| Kind | Holds | Notes |
| --- | --- | --- |
| `spike_shards` | discrete, sorted event times | Written with `spikepack.write_blosc`; same on-disk format as `bwm_ephys` |
| `timeseries` | regularly sampled or explicitly timestamped continuous signals | One store per signal family: position, fluorescence, LFP, photometry, pose |
| `referenced_in_place` | bulk data not converted | Records what re-resolves the file, never only a local path |

`spike_shards` holds discrete event times only. A deconvolved calcium trace is a
value per frame and belongs in a `timeseries` store; thresholding it into event
times is an analysis step, never a conversion step.

Ingestion writes **tick-aligned spike origins**, so the `time_origin_ticks` and
`time_origin_seconds` decoders agree exactly. See `ingestion-notes.md`.

### `ingestion/`
`convert.py` makes the build reproducible. `ingestion-log.md` records what was
done, what was inferred and what was asked. `open-questions.md` records unresolved
items — an analysis agent reads it before using the package.

## Minimum viable package

Ingestion **cannot ship** a package without: `dataset_name`, `dataset_version`, a
`README.md` summary, a declared time base, units for every column of every
declared table and store, `subjects` and `sessions`, `provenance.source`, and for
every declared store either materialised data or a re-resolvable reference.

Ingestion **may ship** without, recording an entry in `open-questions.md`:
`scientific-context.md`, `features/`, per-column prose beyond units, exact
conversion detail for upstream-derived fields, optional modalities.

The skill never invents a unit or a time base to close a blocking gap. It stops
and asks. `a.u.` and `dimensionless` are valid units.

## Versioning

`<dataset_name>/<version>/` is the **package** version, semver.
`provenance.source.version` records the **upstream** version, independently.

- patch — prose or metadata fixes, no data change
- minor — tables, columns or modalities added without breaking existing readers
- major — schema-breaking change

A change of upstream `source.version` forces at least a minor bump.

## Relationship to BWM

BWM is unchanged. Specifically:

- `bwm_ephys` and `bwm_behavior` data files, `schema.yaml`, and the BWM dataset
  builder are untouched.
- `skills/ibl-analyze/` is untouched. Aging and autism use the same IBL task and
  route to the existing guardrails as they stand. `ingestion-notes.md` records the
  audit of BWM-specific assumptions to watch during the pilot.
- BWM's `metadata/events.parquet` already matches the generic `events` contract
  except for the session key (`eid`). The mapping is held **reader-side** — a
  built-in column map for `dataset_kind: bwm` — so no BWM file is rewritten.
- `load_spike_shard` moves from `bwm_ephys.py` to
  `ibl_ai_agent/datasets/spike_store.py`, re-exported from `bwm_ephys` so existing
  imports keep working. A move, not a behaviour change.
- The new routing entry in `AGENTS.md` is additive. The "Brain Wide Map question"
  load packet stays first and unchanged, and the dataset-discovery step must not
  alter which files a BWM question loads. This is a test requirement, not an
  assumption.

Known precision ceiling, not retrofitted: BWM stores `events.event_time` as
float32, whose spacing at t ~ 3000 s is ~0.24 ms — coarser than the 0.1 ms spike
quantization those events are aligned to. Ingested datasets use float64.

## Deferred and open

Deferred by decision, recorded in `ingestion-notes.md`:
- lifting the dataset-independent semantic core out of `skills/ibl-analyze/`
- retiring the in-repo spike encoder in favour of `spikepack`
- the implementation gaps: NWB/DANDI reader, per-lab readers, two-photon reader,
  tracking reader, timeseries container format, generic feature builders, the
  dataset validator, the `spikepack` read-side defect

Open:
- raw data size for the aging and autism datasets
- whether those protocols use biased blocks, which decides whether
  `skills/ibl-analyze/references/prior_and_block_semantics.md` applies

# Data ingestion — design notes

Working notes for the generic data-ingestion skill (branch `ingestion-pilot-aging`).
Scope: let the agent analyse datasets beyond BWM, starting with IBL aging and autism.

## Spike shard format

### Decision: use `spikepack` as the shard writer for ingested datasets

Ingested datasets write spike shards via
[`spikepack`](https://github.com/int-brain-lab/spikepack) (`write_blosc`), generic
over shard key and unit-selection rule. No second shard writer is added to this repo.

Install is from git, not PyPI: `pip install spikepack` returns 404 for both
`spikepack` and `spike-pack` as of 2026-09-29. Pin to a commit SHA in an
optional `ingest` extra until a release is published.

### Decision (deferred, for devs): retire the in-repo encoder at the next BWM version bump

`ibl_ai_agent/datasets/bwm_ephys.py` still carries its own spike encoder
(`_encode_spike_times_dataset`, `SpikeShardWriter`). `spikepack` was extracted and
generalised from exactly that code, so the two are now duplicated logic that can
drift silently.

**Retire the in-repo encoder in favour of `spikepack` at the next `bwm_ephys`
version bump.** Not now: switching the BWM builder today would change the bytes of
a rebuilt release for no scientific gain.

Evidence (verified 2026-09-29 against `bwm_ephys/1.2.1`, probe
`00a824c0-e060-495f-9ebc-79c82fef4c67`, 4,508,958 spikes, read-only):

- **Decoded spike times are identical.** Re-encoding the probe with
  `spikepack.write_blosc` and reading it back with the repo's own
  `load_spike_shard` gives max absolute time error `0.0 s`; `spike_clusters` and
  `cluster_ids` compare equal.
- **The bytes differ.** `spike_times_delta_ticks.blosc` and
  `spike_clusters.blosc` are not byte-identical (5,844,048 B vs 5,844,215 B
  total). Two causes, both benign:
  - spikepack sets `delta[0] = 0` and moves the first spike's offset into
    `time_origin_ticks`; the BWM builder leaves `time_origin_ticks = 0` and puts
    the offset in `delta[0]`. Same reconstructed times, different arrays.
  - Blosc/numcodecs version differences change compressed output for large
    arrays (`cluster_ids` and `cluster_spike_counts` were byte-identical).
- File names, array names, dtypes and codec specs (`blosc/zstd/clevel 7/shuffle`)
  all match. Container is a directory of `.blosc` files, not Zarr.

So the bump is a re-encode, not a re-derivation. Version it as such and note in
the changelog that shard bytes change while spike times do not.

### Decision: shared reader, BWM writer untouched

- Move `load_spike_shard` from `bwm_ephys.py` to
  `ibl_ai_agent/datasets/spike_store.py`, re-exported from `bwm_ephys` so existing
  imports keep working.
- Leave `_encode_spike_times_dataset` and `SpikeShardWriter` in place for now
  (see deferred decision above).
- The shared reader must decode both origin layouts: BWM's offset-in-`delta[0]`
  and spikepack's offset-in-`time_origin_ticks`. Add a test that both give the
  same spike times.

**Caveat for that test — do not assert exact equality unconditionally.** The
current reader already handles both layouts (it computes
`cumsum(deltas) + time_origin_ticks`), but the two decoders disagree on origin
*precision*: `spikepack.decode_times` prefers the float `time_origin_seconds`,
while `load_spike_shard` uses the rounded `time_origin_ticks`. When the first
spike is not tick-aligned, that rounding adds up to half a tick on top of the
per-spike half-tick, so worst-case error is one tick (0.1 ms), not half.

Measured: real BWM shards give `0.0` error (their origins are already
tick-aligned); a synthetic train with a non-aligned origin gave `5.136e-05 s`,
just over the advertised half-tick of `5e-05 s`.

**Resolved: do NOT change `load_spike_shard` to prefer `time_origin_seconds`.**
That looked like the clean fix, but it is not a no-op on existing BWM data.
Checked all 699 shards in `bwm_ephys/1.2.1`: 696 have
`(time_origin_seconds, time_origin_ticks) == (0.0, 0)`, but three have a non-zero,
non-tick-aligned negative origin:

| pid | origin_seconds | ticks x q | shift | n_spikes |
| --- | --- | --- | --- | --- |
| `11a5a93e-58a9-4ed0-995e-52279ec16b98` | -6.453058282515064 | -6.4531 | 41.7 us | 9,141,760 |
| `50f1512d-dd41-4a0c-b3ab-b0564f0424d7` | -2.379225878888514 | -2.3792 | 25.9 us | 2,260,189 |
| `5a34d971-1cb3-4f0e-8dfe-e51e2313a668` | -1.367649417027253 | -1.3676 | 49.4 us | 5,960,054 |

Preferring the float origin would shift every spike time on those three probes by
up to 49.4 us. Below the 100 us quantization and scientifically negligible, but it
is a silent change to existing BWM results and breaks the "BWM behaves exactly as
before" constraint.

Instead: keep `load_spike_shard` using `time_origin_ticks` (current behaviour,
BWM unchanged), and **require the ingestion writer to emit tick-aligned origins**,
which removes the discrepancy at the source. The both-variants test can then
assert exact equality.

### Not doing

Do not retrofit `unit_selection_rule` into existing BWM shards. Ingested datasets
echo it into each shard's `meta.json`; BWM continues to record it in
`provenance.yaml` only.

## Upstream defects found in `spikepack` 0.1.0 (commit `30ab06f`)

Worth filing against `int-brain-lab/spikepack`:

1. **`read_blosc` silently loses cluster assignments on real BWM shards.**
   `_restore` gates on `meta["has_labels"]` / `meta["has_cluster_ids"]`, which are
   spikepack-only keys absent from shipped BWM shards. Reading
   `bwm_ephys/1.2.1` returns `['meta', 'times']` — no labels, no `cluster_ids`,
   no error raised. spikepack is safe as a *writer* of our format but not
   currently safe as a *reader* of existing BWM data.
2. **Format-string mismatch.** Shipped `bwm_ephys/1.2.1` shards carry
   `"format": "ibl_agent_spike_shard_v2"`; spikepack and current `bwm_ephys.py`
   both write `"ibl_ai_agent_spike_shard_v2"`. Harmless only because
   `load_spike_shard` never checks the field — any format gate we add would
   misfire on the shipped release.
3. **`docs/reference/format.qmd` is stale.** It documents arrays as
   `event_times_delta_ticks` / `event_labels`; the code writes
   `spike_times_delta_ticks`, `spike_clusters`, `cluster_ids`,
   `cluster_spike_counts`.
4. **README install line is wrong** — `pip install spikepack` does not resolve.

## Skill layering

### Decision (deferred, for devs): lift the dataset-independent semantic core out of `ibl-analyze`

Target design: a dataset-neutral analysis skill that every dataset gets, leaving
`ibl-analyze` holding only the IBL/BWM-specific material. **Not in this piece of
work** — it edits the skill governing all BWM analysis, and the pilot does not
need it (see next decision).

Proposed seam, verified by reading every file under `skills/ibl-analyze/`:

Generic (lift):
- metric classification: direct / operationalized / proxy, and the semantic match gate
- shape-before-scalar validation
- independent statistical unit / pseudoreplication rules
- ambiguity policy (plausible definitions, stored vs recomputed vs unavailable)
- `references/reproducibility_qc.md` — general statistical hygiene, QC reporting
- `references/scientific_caveats/` — both cards are already dataset-neutral
- `references/interactive_scientific_analysis.md` — the whole lifecycle is portable

IBL-specific (leave behind):
- event anchors (`stimOn_times`, `firstMovement_times`, `feedback_times`, `goCue_times`)
- `probabilityLeft` / block-prior semantics, `references/prior_and_block_semantics.md`
- BWM region and inclusion guidance, `references/bwm_analysis_patterns.md`,
  `references/visual_latency.md`, the BWM routing rows in `references/operators.md`

When this move happens it must be pure motion — no rewording — verifiable by diff
and by `tests/test_skill_references.py`.

### Decision: pilot routes to `ibl-analyze` as it stands

Aging and autism use the same IBL task, so route them to the existing guardrails
unchanged. Audit of BWM-specific assumptions that could mislead on those datasets
is recorded below; treat it as the list to check during the pilot, not as work to do now.

## Audit: BWM assumptions in `ibl-analyze` that could mislead on aging/autism

### Routing — would send the agent to data that does not exist for these datasets
1. `SKILL.md` default policy #7: "Prefer local BWM tables and shards when their
   schema covers the question." No instruction on where to go when it does not.
2. `references/operators.md` — the Operator Map and "BWM Loading Route" name
   `bwm_ephys` / `bwm_behavior` / `bwm_query` / `bwm_units` as the surfaces for
   good units, movement/quiescence, passive, and metadata questions. Dead ends here.
3. `references/operators.md` General Rules repeats the same BWM preference.
4. `references/visual_latency.md` Inputs prefer `bwm_ephys` tables and
   `event_response_features.parquet`, with `brainwidemap.load_good_units` as the
   fallback — the fallback routes *into* the BWM release helper.
5. `references/bwm_analysis_patterns.md` is BWM throughout. Conditionally routed,
   so lower risk, but "Apply the BWM trial mask before event-aligned statistics"
   has no analogue in aging/autism and would be silently skipped or wrongly sought.

### Inclusion and QC
6. The BWM trial mask (`bwm_include` in `trials.parquet`) has no equivalent. The
   inclusion rule must become dataset-declared.
7. `references/reproducibility_qc.md`: "Prefer canonical release QC when available
   over improvised local thresholds." Aging/autism may have no canonical release QC;
   risk is the agent quietly borrows BWM's `label >= 1.0` or invents a threshold.
8. Nothing in `ibl-analyze` ever asks what the unit-selection rule *was*. Ingested
   packages declare `unit_selection_rule`; the skill needs to read it.

### Subject and design — the largest gap for these two datasets
9. `references/reproducibility_qc.md` is framed entirely on cross-**lab**
   reproducibility (12 labs, RIGOR QC, "when comparing labs or regions"). Aging and
   autism are plausibly single- or few-lab, making "lab" a degenerate variance
   dimension. Its robust/fragile lists are evidence from BWM repeated-site
   recordings, not a general law.
10. Throughout, coverage is reported as "unit / insertion / session / subject / lab":
    **subject appears only as a coverage dimension, never as an experimental factor.**
    For aging, age is a continuous between-subject covariate; for autism, genotype is
    a between-subject factor. Nothing covers between-subject designs, group
    comparisons, or age as a covariate. The statistical-unit rule correctly says
    neurons nested in a subject are not independent, but stops short of saying that
    in a between-subject design N is *subjects*, and typically small.
11. No caveat for **age or genotype confounded with recording quality** — older mice
    or a mutant line may differ in yield, stability, drift, or engagement, producing
    apparent neural group differences. This is the across-subject analogue of
    `scientific_caveats/firing_rate_nonstationarity.md` and does not exist.

### Task — conditional on an unresolved fact
12. `references/prior_and_block_semantics.md` and the `probabilityLeft` guidance
    assume the **biased-block full task**. `ibl-load/references/ibl_behavior_task.md`
    itself warns to distinguish the equal-probability basic task from the biased-block
    full task. **Open question: do aging and autism use biased blocks?** If not, all
    prior/block guidance is inapplicable.
13. `ibl-load/references/bwm_release_scope.md` anchors scale at 621,733 neurons /
    699 probes / 139 mice / 12 labs. Conditionally routed, but if it lands in context
    for an aging question it anchors expectations wrongly.

### Confirmed portable
`references/interactive_scientific_analysis.md`, both `scientific_caveats/` cards,
and the shape-before-scalar / semantic-match / statistical-unit sections of
`references/scientific_context_and_metric_semantics.md` carry across unchanged.
This is the evidence for the seam above.

## Package contract decisions

### Item 2 (fixed): `age_at_session` belongs on `sessions`, not `subjects`
`subjects.parquet` carries `dob`; `sessions.parquet` carries `age_at_session_days`,
computed at ingestion and declared with units. Age varies by session and is the
primary scientific variable for the aging dataset — one age per subject would
silently destroy its main axis.

### Item 5 (fixed): referenced-in-place stores must be re-resolvable
A `kind: referenced_in_place` entry records what is needed to *re-resolve* the file
(e.g. ONE `eid`, dataset name, collection, revision), not a machine-local path. A
local path may be cached alongside as a hint, never as the only locator.

### Item 4 (resolved): two version axes
`<name>/<version>/` is the **package** version (semver). `provenance.yaml`
`source.version` records the **upstream** version independently. Bump rules:
- patch — prose, metadata or documentation fixes only, no data change;
- minor — tables/columns/modalities added without breaking existing readers;
- major — schema-breaking change.
A change of upstream `source.version` always forces at least a minor bump.

### Item 7 (resolved): minimum viable package
Blocking — ingestion cannot ship the package without:
`dataset_name`, `dataset_version`, `README.md` summary, a declared `time_base`,
**units for every column of every declared table and store**, `subjects` and
`sessions` tables, `provenance.source`, and for every declared store either
materialised shards or a re-resolvable reference.

The units rule was originally scoped to *required* tables only. Tightened to all
declared tables and stores, because `features/`, conditional tables and timeseries
stores are exactly where imaging and LFP data land — the narrower rule would have
held for the pilot and failed generally. `a.u.` and `dimensionless` are valid
units, so fluorescence and dF/F do not stall ingestion.

Non-blocking — ship with an `ingestion/open-questions.md` entry:
`scientific-context.md`, `features/`, per-column prose beyond units, exact
conversion detail for upstream-derived fields, and optional modalities.

The skill never invents a unit or a time base to fill a blocking gap; it stops and asks.

### Item 8 (resolved): generic `events` table, BWM maps via a reader-side view
Generic contract: `session_id`, `event_id`, `event_name`, `event_time`
(seconds, **float64**, in the declared `time_base`), plus nullable `trial_id`
(null for non-trial-based experiments) and nullable `event_value`. Extra
denormalised columns are tolerated.

BWM's existing `metadata/events.parquet` already matches on `event_id`,
`event_name`, `event_time`, `trial_id`; only the session key differs (`eid`).
**Do not edit BWM's table or its `schema.yaml`.** The reader holds the mapping:
`dataset_kind: bwm` uses a built-in column map (`session_id` <- `eid`); ingested
datasets declare `column_map` in their own `schema.yaml`.

Precision note: BWM stores `event_time` as **float32**. At t ~ 3000 s float32
spacing is ~0.24 ms, coarser than the 0.1 ms spike quantization. Ingested datasets
must use float64. Not retrofitted to BWM.

### Items 3 and 6 (accepted): fixed section headings, and a dataset-discovery step
Prose files use fixed section headings so a loader can pull one section instead of a
whole file. `AGENTS.md` gains a discovery step that enumerates configured datasets
and reads their one-paragraph summaries.

**Constraint: existing BWM routing must behave identically.** The new Required Load
Packet is additive — the "Brain Wide Map question" packet stays first and unchanged,
and discovery must not alter which files a BWM question loads.

## Open questions
- **Data size** for the aging and autism raw datasets — pending. Shard conversion
  is the long pole; BWM's feature-refresh stage alone took 4,225 s over 699 probes.
- **Do aging and autism use biased blocks?** Determines whether
  `prior_and_block_semantics.md` applies (audit item 12).

## Stress test: five data types

Cases tested: (a) hippocampus during free exploration, no trials; (b) two-photon
calcium imaging, no spikes, possibly deconvolved; (c) NWB from DANDI; (d) a lab's
own format with only a README; (e) IBL aging and autism.

### Structural problems — fixed in the proposal

S1. **No store for continuous timeseries.** Broke (a) position/head-direction,
    (b) fluorescence traces, (c) NWB `TimeSeries`, (d) ECoG/EMG/photometry.
    `events` holds instants and `epochs` holds labelled intervals; neither holds a
    sampled signal. BWM avoided this by reducing wheel/pose to trial-aligned
    features, which is impossible without trials.
    Fix: a `timeseries` store kind — one store per signal family, declaring its
    sources, `rate_hz` + `t0` *or* an explicit timestamps array, units, time base
    and container format; chunked for interval reads.

S2. **`spikes` store was undefined w.r.t. continuous rate estimates.** Deconvolved
    2P traces are a value per frame, not sorted event times, and must not be
    quantized into the spike shard.
    Fix: `spikes` is discrete event times only; deconvolved/continuous rate
    estimates are a `timeseries` store. Thresholding to events is an analysis step,
    never a conversion step.

S3. **Required-table list assumed electrophysiology.** `channels` is meaningless for
    2P and `units` are ROIs.
    Fix: core tables `subjects`, `sessions`, `recordings`, `events`, `epochs`
    (last two required-present, may be empty); conditional tables `units`
    (discrete sorted/segmented sources), `channels` (electrode-based only),
    `trials` (trial-based only).

S4. **Multiple clocks unrepresentable.** NWB timestamps are per-`TimeSeries` and need
    not share a clock; `time_bases:` was plural but nothing bound a table or store to one.
    Fix: every table and store names its `time_base`; `time_bases:` declares each
    base's origin, clock and alignment to the others.

S5. **No spatial reference frame.** Free-exploration position needs an arena origin,
    axes and length units; `time_bases` only covers time.
    Fix: a `reference_frames:` block alongside `time_bases:`.

S6. **Overlapping epoch vocabularies collided.** "immobile" and "in zone A" are two
    independent labelings of the same session; one flat `label` column cannot
    distinguish them.
    Fix: `epochs` gains `epoch_set`, a labeling namespace. Overlapping sets coexist.

S7. **No slot for experimental design.** Which factors are between-subject (age,
    genotype), which within, what the groups are, what comparison the experiment was
    built for. The most important fact about the aging and autism datasets had
    nowhere to live except free prose. Matches audit item 10 (subject treated as a
    coverage dimension, never as an experimental factor).
    Fix: a machine-readable `design:` block in `schema.yaml` — each factor with
    levels and grain (between-subject / within-subject / between-session) and the
    intended comparison — plus a required `experiment.md` section "Design and factors".

S8. **`unit_selection_rule` presumed spike sorting.** Sources may be ROIs.
    Fix: renamed `source_selection_rule`.

Also folded in: the "units for every column" blocking rule accepts `a.u.` and
`dimensionless` (fluorescence, dF/F), so ingestion does not stall on a non-problem.

### Verified: events/epochs represent non-IBL behaviour without schema change

`events` = named instants, optional scalar `event_value`, plus dataset-declared
extra columns (tone frequency, zone identity). `epochs` = named intervals within a
declared `epoch_set`. Reward delivery, licks, zone entries, optogenetic pulses,
sleep states, drug on/off, and nested trial-within-session structure all express
without touching the contract.

### Implementation gaps — future work, no layout change needed

I1. **NWB/DANDI reader.** NWB `Units` -> `units`, `TimeIntervals` -> `trials`/`epochs`,
    `Subject` -> `subjects`, `TimeSeries` -> `timeseries` stores, dandiset ID +
    version + asset path -> `provenance.source`. Mapping is mechanical.
    Note the tension: NWB is already self-describing, so converting it duplicates
    work. Metadata conversion is cheap; spike shards earn their keep on size.
I2. **Per-lab format readers**, for the README-only case. The blocking-gap rules
    already make the agent stop and ask rather than invent units or a time base.
I3. **Two-photon reader** (Suite2p / CaImAn): ROI tables with pixel masks, plane
    index and imaging depth; F / Fneu / dF/F / deconvolved traces as timeseries
    stores; per-plane frame times with plane offsets.
I4. **Position/tracking reader** for free exploration: position, head direction,
    speed as timeseries, in a declared spatial reference frame.
I5. **Timeseries container format.** Codec and chunking for the `timeseries` store
    (zarr vs blosc shards). The store kind is declared per store, so choosing the
    format later is not a layout change.
I6. **Generic feature builders.** `_build_event_response_features` and
    `_build_unit_features` live inside `bwm_ephys.py`. Aging and autism need
    BWM-schema features for `bwm_analysis_patterns.md` guidance to transfer; lift
    them out so any dataset can build them.
I7. **Dataset validator** (`validate-dataset`): declared tables exist, primary keys
    unique, every column has units and a description, shard keys resolve, every
    table and store names a valid time base, referenced-in-place entries re-resolve.
I8. **spikepack read-side defect** — either upstream fix or a repo-side wrapper, so
    reading existing BWM shards through spikepack does not silently drop labels.

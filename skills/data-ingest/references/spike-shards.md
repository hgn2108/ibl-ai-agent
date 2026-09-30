# Spike shards

Read this before anything else if the dataset has spikes to convert. If it has
none, or its spikes are referenced in place by decision, skip the preflight and
record in the log that it was skipped and why.

## Preflight
Run this first, so that a missing or outdated environment fails before a long
read of the source rather than after it.

```bash
uv run python -c "import sys, spikepack; print(sys.version.split()[0], spikepack.__version__)"
```

- **Python < 3.11: stop.** `spikepack` requires Python >=3.11, and the repo's
  `ingest` extra carries the marker `python_version >= '3.11'`, so on the repo's
  3.10 floor it resolves to nothing. Explain this and stop. Do not install
  anything, and do not substitute another shard writer.
- **Python ≥ 3.11 but `spikepack` missing: ask.** Offer to run
  `uv sync --extra ingest`, and do not install unprompted. If the user declines,
  stop. The `ingest` extra is still pending (`pyproject.toml`). On a checkout
  without it the sync fails, so say so rather than retrying.
  **During the pilot** you may instead offer to install the pinned commit
  directly:
  `uv pip install "spikepack @ git+https://github.com/int-brain-lab/spikepack@30ab06ff7794d89cab17cb54338db869ad90d036"`.
  Ask first, and log it as a pilot stand-in for the `ingest` extra. A later
  `uv sync` will remove it.
- Record the interpreter version, the `spikepack` version (or its absence) and
  the install decision. The package directory doesn't exist yet, so carry this
  forward into `ingestion/ingestion-log.md`.

`spikepack` is `int-brain-lab/spikepack` (MIT). It is installed from git and
pinned by SHA in the `ingest` extra, not from PyPI.

## Writing shards
`spikepack.write_blosc` is the only shard writer for ingested datasets.

**Snap every spike time to the quantization grid before calling it.** Only
tick-aligned origins make the `time_origin_ticks` and `time_origin_seconds`
decoders agree exactly:

```python
q = quantization_us
times_seconds = np.rint(times_seconds * 1e6 / q) * q / 1e6
```

Snapping moves each spike by at most half a tick, the same bound the encoder
already applies. Record it under `provenance.yaml` `conversion.lossy`.

`extra_meta` carries at least: `dataset_name`, `dataset_version`, `shard_key`,
`shard_id`, `session_id`, `subject_id`, `source_selection_rule`, `time_base`,
`n_spikes`, `n_units`, `cluster_encoding`, `time_encoding`, `compression`.

A `spike_shards` store holds discrete event times only. A deconvolved calcium
trace belongs in a `timeseries` store. Thresholding it into events is an
analysis step, never a conversion step.

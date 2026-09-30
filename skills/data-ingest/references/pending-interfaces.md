# Interfaces pending implementation

The skill is written against these interfaces, and none of them exists yet.
Check before calling one. If it is missing, stop and tell the user. Do not
reimplement it inside `ingestion/convert.py`, except under the pilot exception in
`SKILL.md` hard rule 3.

- `ibl_ai_agent/datasets/spike_store.py`: `load_spike_shard`, moved from
  `bwm_ephys.py` and re-exported from it. A move, not a behaviour change. This
  is the read side only; ingestion writes through `spikepack`.
- `ibl_ai_agent/datasets/one_trials.py`: loads `trials` per session through ONE
  and returns one concatenated DataFrame with an `eid` column, which is the
  extraction's input. It lives in the repo, with a test, because every package
  needs identical behaviour from it.
- `bwm_simple._build_trials`: will accept a path or a DataFrame, with `roster`
  optional. With `roster=None` the roster filter and merge are skipped, and
  `subject`, `date`, `session_number` and `lab` are not emitted.
- `bwm_ephys._build_events`: will gain a keyword-only `event_time_dtype`
  (default `np.float32`) and keyword-only control of the session key and carried
  columns. Ingested packages pass `np.float64`. The cast happens inside the
  function, so up-casting its output afterwards would not recover the precision.
- `pyproject.toml` `ingest` extra: see `spike-shards.md`.

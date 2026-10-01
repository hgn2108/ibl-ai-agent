"""Build the ibl_aging dataset package from the OpenAlyx release 2025_Q3_Zang_et_al_Aging.

Run from the ibl-ai-agent repo with `.venv/bin/python <package>/ingestion/convert.py`
(not `uv run`/`uv sync`: spikepack is installed outside the lockfile during the pilot).
Reads only through ONE; the S3 cache is read-only and never written to.
"""
import argparse
import hashlib
import json
import multiprocessing as mp
import resource
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import spikepack
import yaml
from iblatlas.regions import BrainRegions
from ibllightning import OneLightningAI

from ibl_ai_agent.datasets.bwm_ephys import EVENT_COLUMNS

DATASET_NAME = "ibl_aging"
DATASET_VERSION = "1.0.0"
REPO_DIR = Path("/teamspace/studios/this_studio/ibl-ai-agent-ingest")
PACKAGE_DIR = Path("/teamspace/studios/this_studio/datasets") / DATASET_NAME / DATASET_VERSION
RELEASE_TAG = "2025_Q3_Zang_et_al_Aging"
BWM_SORT_TAG = "2024_Q2_IBL_et_al_BWM_iblsort"  # the aging tag carries no sorting for BWM probes
BWM_SORT = ("pykilosort", "2024-05-06")
AGING_SORT = ("iblsorter", None)
QUANTIZATION_US = 100
GOOD_UNIT_LABEL = 1.0
SOURCE_SELECTION_RULE = "clusters.metrics label == 1 (all three IBL single-unit metrics pass); user decision"
SUBJECT_STRAIN = "C57BL/6"  # user answer, from the paper; Alyx has no strain for these subjects
ONE_KWARGS = dict(
    base_url="https://openalyx.internationalbrainlab.org", password="international", silent=True,
    cache_dir="/teamspace/s3_connections/ibl-brain-wide-map-public/data",
    tables_dir="/teamspace/studios/this_studio/Downloads/ONE/openalyx_tables",
)
TRIALS_REQUIRED = ["eid", "intervals_0", "intervals_1", "stimOn_times", "contrastLeft", "contrastRight", "choice", "feedbackType"]
# Canonical order of bwm_simple._build_trials, roster columns and bwm_include removed.
TRIALS_ORDER = ["eid", "trial_id", "choice", "feedbackType", "probabilityLeft", "contrastLeft", "contrastRight",
                "intervals_0", "stimOn_times", "goCue_times", "firstMovement_times", "response_times",
                "feedback_times", "intervals_1", "goCueTrigger_times", "stimOff_times", "rewardVolume", "reaction_time"]


def load_release(one):
    sessions = pd.DataFrame(one.alyx.rest("sessions", "list", tag=RELEASE_TAG))
    insertions = pd.DataFrame(one.alyx.rest("insertions", "list", tag=RELEASE_TAG))
    bwm_eids = set(map(str, one.search(tag=BWM_SORT_TAG, query_type="remote")))
    trials_ds = pd.DataFrame(one.alyx.rest("datasets", "list", tag=RELEASE_TAG, name="_ibl_trials.table.pqt"))
    sorted_ds = pd.DataFrame(one.alyx.rest("datasets", "list", tag=RELEASE_TAG, name="spikes.times.npy"))
    subjects = pd.DataFrame([one.alyx.rest("subjects", "read", id=s) for s in sorted(sessions.subject.unique())])
    return sessions, insertions, bwm_eids, trials_ds, sorted_ds, subjects


def dataset_eid(url):
    return str(url).rstrip("/").split("/")[-1]


# PILOT STAND-IN for ibl_ai_agent/datasets/one_trials.py
def load_trials(one, eids, revisions):
    frames = []
    for eid in eids:
        tr = one.load_object(eid, "trials", collection="alf", revision=revisions.get(eid) or None)
        tr.pop("intervals_bpod", None)
        tr.pop("table", None)
        df = tr.to_df() if hasattr(tr, "to_df") else pd.DataFrame(tr)
        df.insert(0, "eid", eid)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


# PILOT STAND-IN for bwm_simple._build_trials(trials, roster=None)
def build_trials(trials, biased_blocks):
    missing = [c for c in TRIALS_REQUIRED if c not in trials.columns]
    if missing:
        raise KeyError(f"trials missing required columns {missing}")
    trials = trials.copy()
    trials["trial_id"] = trials.groupby("eid").cumcount().astype(np.int32)
    order = [c for c in TRIALS_ORDER if c in trials.columns and (biased_blocks or c != "probabilityLeft")]
    return trials[order], [c for c in TRIALS_ORDER if c not in trials.columns]


# PILOT STAND-IN for bwm_ephys._build_events(trials, event_time_dtype=np.float64, session key/carried columns)
def build_events(trials):
    rows = []
    for event_name, source_column in EVENT_COLUMNS:
        if source_column not in trials.columns:
            continue
        ev = trials[["eid", "trial_id", source_column]].rename(columns={source_column: "event_time"})
        ev["event_name"] = event_name
        rows.append(ev.loc[ev.event_time.notna()])
    events = pd.concat(rows, ignore_index=True)
    events["event_time"] = events["event_time"].astype(np.float64)
    events.sort_values(["eid", "trial_id", "event_time", "event_name"], inplace=True, kind="mergesort")
    events["event_id"] = events.groupby("eid").cumcount().astype(np.int32)
    events["event_value"] = np.nan
    events = events.rename(columns={"eid": "session_id"})
    return events[["session_id", "event_id", "event_name", "event_time", "trial_id", "event_value"]].reset_index(drop=True)


def convert_recording(one, br, rec, spikes_dir):
    """Units, channels and one spike shard for one probe; skips the shard if already written."""
    eid, probe, sorter, rev = rec.session_id, rec.probe_name, rec.sorter, rec.sorting_revision
    rev = rev if isinstance(rev, str) and rev else None  # parquet/pandas turn None into NaN
    coll = f"alf/{probe}/{sorter}"
    metrics = one.load_dataset(eid, "clusters.metrics.pqt", collection=coll, revision=rev)
    clusters = one.load_object(eid, "clusters", collection=coll, revision=rev, attribute=["channels", "depths", "uuids"])
    channels = one.load_object(eid, "channels", collection=coll, revision=rev,
                               attribute=["brainLocationIds_ccf_2017", "mlapdv", "localCoordinates", "rawInd"])
    atlas_id = np.asarray(channels["brainLocationIds_ccf_2017"]).astype(np.int64)
    xyz = np.asarray(channels["mlapdv"], dtype=np.float64)
    local = np.asarray(channels["localCoordinates"], dtype=np.float64)
    ch = pd.DataFrame({
        "recording_id": rec.recording_id, "session_id": eid, "channel_id": np.arange(len(atlas_id), dtype=np.int32),
        "raw_index": np.asarray(channels["rawInd"]).astype(np.int32), "atlas_id": atlas_id,
        "acronym": br.id2acronym(atlas_id), "beryl_acronym": br.id2acronym(atlas_id, mapping="Beryl"),
        "x": xyz[:, 0], "y": xyz[:, 1], "z": xyz[:, 2], "lateral_um": local[:, 0], "axial_um": local[:, 1],
    })
    good = metrics.loc[metrics.label >= GOOD_UNIT_LABEL].copy()
    cid = good.cluster_id.to_numpy()
    cch = np.asarray(clusters["channels"])[cid]
    uuids = clusters["uuids"]
    uuids = (uuids.iloc[:, 0] if isinstance(uuids, pd.DataFrame) else pd.Series(uuids)).to_numpy()
    units = pd.DataFrame({
        "recording_id": rec.recording_id, "session_id": eid, "cluster_id": cid.astype(np.int32),
        "cluster_uuid": uuids[cid].astype(str), "channel_id": cch.astype(np.int32),
        "atlas_id": atlas_id[cch], "acronym": ch.acronym.to_numpy()[cch], "beryl_acronym": ch.beryl_acronym.to_numpy()[cch],
        "x": xyz[cch, 0], "y": xyz[cch, 1], "z": xyz[cch, 2], "depth_um": np.asarray(clusters["depths"])[cid],
        "label": good.label.to_numpy(), "firing_rate": good.firing_rate.to_numpy(), "spike_count": good.spike_count.to_numpy().astype(np.int64),
        "amp_median": good.amp_median.to_numpy(), "presence_ratio": good.presence_ratio.to_numpy(),
        "contamination": good.contamination.to_numpy(), "drift": good.drift.to_numpy(),
        "slidingRP_viol": good.slidingRP_viol.to_numpy(), "noise_cutoff": good.noise_cutoff.to_numpy(),
    })
    shard = spikes_dir / rec.recording_id
    if (shard / "meta.json").exists():
        n_spikes = json.loads((shard / "meta.json").read_text())["n_spikes"]
    else:
        sp = one.load_object(eid, "spikes", collection=coll, revision=rev, attribute=["times", "clusters"])
        keep = np.isin(sp["clusters"], cid)
        q = QUANTIZATION_US
        times = np.rint(np.asarray(sp["times"])[keep] * 1e6 / q) * q / 1e6
        labels = np.asarray(sp["clusters"])[keep].astype(np.int32)
        n_spikes = int(keep.sum())
        spikepack.write_blosc(shard, times_seconds=times, labels=labels, cluster_ids=cid.astype(np.int32),
                              quantization_us=q, extra_meta={
            "dataset_name": DATASET_NAME, "dataset_version": DATASET_VERSION, "shard_key": "recording_id",
            "shard_id": rec.recording_id, "session_id": eid, "subject_id": rec.subject_id, "probe_name": probe,
            "sorter": sorter, "sorting_revision": rev, "source_selection_rule": SOURCE_SELECTION_RULE,
            "time_base": "session_clock", "n_spikes": n_spikes, "n_units": int(len(cid)),
            "cluster_encoding": "cluster_id", "time_encoding": f"delta_ticks_{q}us", "compression": "blosc_zstd_clevel7_shuffle",
        })
    return units, ch, n_spikes


_WORKER = {}


def _init_worker(one=None, br=None):
    """Give this process its own ONE connection; a connection is not shared across processes."""
    _WORKER["one"] = one or OneLightningAI(**ONE_KWARGS)
    _WORKER["br"] = br or BrainRegions()


def _convert_task(rec, spikes_dir):
    """Convert one probe in this process; returns (result, error, seconds, peak RSS of this process in GB)."""
    t0 = time.time()
    try:
        out, err = convert_recording(_WORKER["one"], _WORKER["br"], SimpleNamespace(**rec), spikes_dir), None
    except Exception as e:  # keep going; failures are reported in the log
        out, err = None, repr(e)
    return out, err, time.time() - t0, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6


def build(out_dir, eids=None, workers=1):
    t_start = time.time()
    one = OneLightningAI(**ONE_KWARGS)
    br = BrainRegions()
    sessions_raw, insertions_raw, bwm_eids, trials_ds, sorted_ds, subjects_raw = load_release(one)
    sessions_raw["id"] = sessions_raw.id.astype(str)
    if eids is not None:
        sessions_raw = sessions_raw[sessions_raw.id.isin(eids)]
    out_dir = Path(out_dir)
    (out_dir / "metadata").mkdir(parents=True, exist_ok=True)
    (out_dir / "spikes").mkdir(exist_ok=True)

    # subjects
    subjects_raw = subjects_raw[subjects_raw.nickname.isin(sessions_raw.subject)]
    subjects = pd.DataFrame({
        "subject_id": subjects_raw.nickname, "subject_uuid": subjects_raw.id.astype(str), "lab": subjects_raw.lab,
        "sex": subjects_raw.sex, "dob": pd.to_datetime(subjects_raw.birth_date).dt.date,
        "strain": SUBJECT_STRAIN, "line": None, "genotype": None, "cohort": None,
    }).sort_values("subject_id").reset_index(drop=True)

    # trials and events, using each session's default tagged trials revision
    trials_ds["eid"] = trials_ds.session.map(dataset_eid)
    default_rev = trials_ds[trials_ds.default_dataset].set_index("eid").revision.to_dict()
    trials_raw = load_trials(one, sessions_raw.id.tolist(), default_rev)
    biased = bool(trials_raw.probabilityLeft.isin([0.2, 0.8]).groupby(trials_raw.eid).any().all())
    trials, trials_skipped = build_trials(trials_raw, biased_blocks=biased)
    events = build_events(trials)
    trials = trials.rename(columns={"eid": "session_id"})

    # sessions
    s = sessions_raw.merge(subjects[["subject_id", "dob"]], left_on="subject", right_on="subject_id")
    extent = trials.groupby("session_id").agg(n_trials=("trial_id", "size"), task_start=("intervals_0", "min"), task_stop=("intervals_1", "max"))
    sessions = pd.DataFrame({
        "session_id": s.id, "subject_id": s.subject, "date": pd.to_datetime(s.start_time.str[:10]).dt.date,
        "session_number": s.number.astype(np.int16), "start_time": pd.to_datetime(s.start_time, format="ISO8601"),
        "protocol": s.task_protocol, "lab": s.lab, "rig": None,
        "in_bwm_release": s.id.isin(bwm_eids),
        "trials_revision": s.id.map(default_rev).fillna(""),
    })
    sessions["age_at_session_days"] = (pd.to_datetime(sessions.date) - pd.to_datetime(s.dob.values)).dt.days.astype(np.float64)
    sessions = sessions.merge(extent, left_on="session_id", right_index=True, how="left")
    sessions["task_duration_s"] = sessions.task_stop - sessions.task_start
    sessions = sessions.drop(columns=["task_start", "task_stop"]).sort_values(["subject_id", "start_time"]).reset_index(drop=True)

    # recordings: BWM probes use the BWM iblsort sorting; the others use what the aging tag carries
    ins = insertions_raw.assign(session_id=insertions_raw.session.astype(str))
    ins = ins[ins.session_id.isin(sessions.session_id)]
    sorted_ds["eid"] = sorted_ds.session.map(dataset_eid)
    tagged = set(zip(sorted_ds.eid, sorted_ds.collection.str.split("/").str[1]))
    in_bwm = ins.session_id.isin(bwm_eids)
    has_aging_sort = [(e, p) in tagged for e, p in zip(ins.session_id, ins.name)]
    recordings = pd.DataFrame({
        "recording_id": ins.id.astype(str), "session_id": ins.session_id, "probe_name": ins.name,
        "subject_id": ins.session_info.map(lambda x: x["subject"]), "device": "neuropixels", "probe_model": ins.model,
        "probe_serial": ins.serial, "alyx_qc": ins.json.map(lambda j: (j or {}).get("qc")),
        "sync_source": "ibllib ephys sync to session main clock",
        "sorter": np.where(in_bwm, BWM_SORT[0], np.where(has_aging_sort, AGING_SORT[0], None)),
        "sorting_revision": [BWM_SORT[1] if b else None for b in in_bwm],
        "sorting_release_tag": np.where(in_bwm, BWM_SORT_TAG, np.where(has_aging_sort, RELEASE_TAG, None)),
    }).sort_values(["session_id", "probe_name"]).reset_index(drop=True)
    recordings["has_spikes"] = recordings.sorter.notna()

    # units, channels, spike shards; probes are independent, so they may run in worker processes
    todo = [r._asdict() for r in recordings[recordings.has_spikes].itertuples(index=False)]
    results, failures = {}, {}
    pool = ProcessPoolExecutor(workers, mp_context=mp.get_context("spawn"), initializer=_init_worker) if workers > 1 else nullcontext()
    with pool:
        if workers > 1:
            futures = {pool.submit(_convert_task, r, out_dir / "spikes"): r for r in todo}
            done = ((futures[f], f.result()) for f in as_completed(futures))
        else:
            _init_worker(one, br)
            done = ((r, _convert_task(r, out_dir / "spikes")) for r in todo)
        for i, (rec, (out, err, seconds, peak_gb)) in enumerate(done, 1):
            if err is None:
                results[rec["recording_id"]] = out
            else:
                failures[rec["recording_id"]] = err
            print(f"[{i}/{len(todo)}] {rec['recording_id']} {seconds:.1f}s peak_rss={peak_gb:.2f}GB"
                  f"{' FAILED ' + err if err else ''}", flush=True)
    # collect in recordings order, so the tables don't depend on which worker finished first
    ok = [r["recording_id"] for r in todo if r["recording_id"] in results]
    units_all = [results[k][0] for k in ok]
    channels_all = [results[k][1] for k in ok]
    n_spikes = {k: results[k][2] for k in ok}
    units = pd.concat(units_all, ignore_index=True)
    channels = pd.concat(channels_all, ignore_index=True)
    recordings["n_good_units"] = recordings.recording_id.map(units.groupby("recording_id").size()).fillna(0).astype(np.int32)
    recordings["conversion_error"] = recordings.recording_id.map(failures)
    sessions["n_recordings"] = sessions.session_id.map(recordings.groupby("session_id").size()).astype(np.int16)
    sessions["n_good_units"] = sessions.session_id.map(units.groupby("session_id").size()).fillna(0).astype(np.int32)

    epochs = pd.DataFrame({"session_id": pd.Series(dtype=str), "epoch_set": pd.Series(dtype=str), "epoch_id": pd.Series(dtype=np.int32),
                           "label": pd.Series(dtype=str), "start_time": pd.Series(dtype=np.float64), "stop_time": pd.Series(dtype=np.float64)})
    tables = dict(subjects=subjects, sessions=sessions, recordings=recordings, events=events, epochs=epochs,
                  units=units, channels=channels, trials=trials)
    for name, df in tables.items():
        df.to_parquet(out_dir / "metadata" / f"{name}.parquet", index=False)

    write_contract(out_dir, tables, biased, trials_skipped, failures, time.time() - t_start)
    return dict(tables=tables, failures=failures, n_spikes=n_spikes, biased=biased, trials_skipped=trials_skipped)


def write_contract(out_dir, tables, biased, trials_skipped, failures, seconds):
    schema = yaml.safe_load((Path(__file__).parent / "schema_source.yaml").read_text())
    for name, spec in schema["tables"].items():
        declared, actual = set(spec["columns"]), set(tables[name].columns)
        if name == "trials":
            declared &= actual | {c for c in declared if c not in TRIALS_ORDER}  # optional columns may be absent
        if declared != actual:
            raise ValueError(f"{name}: schema columns differ from table: {sorted(declared ^ actual)}")
    schema["tables"]["trials"]["columns"] = {c: schema["tables"]["trials"]["columns"][c] for c in tables["trials"].columns}
    (out_dir / "schema.yaml").write_text(yaml.safe_dump(schema, sort_keys=False, width=100))

    provenance = {
        "source": {"url": "https://openalyx.internationalbrainlab.org", "release_tag": RELEASE_TAG,
                   "spike_sorting_release_tag_bwm_probes": BWM_SORT_TAG, "doi": "10.1101/2025.08.22.671763",
                   "lab": "International Brain Laboratory (12 labs)", "contact": "not stated",
                   "version": RELEASE_TAG, "access": "public"},
        "conversion": {
            "steps": [
                "list sessions, insertions and subjects tagged with the release on OpenAlyx",
                "load trials per session through ONE at the session's default tagged revision",
                "build trials (canonical IBL columns) and events (float64 seconds) with pilot stand-ins",
                "per probe: load clusters.metrics, clusters and channels from the chosen sorting; keep label == 1",
                "per probe: load spikes.times/clusters, keep good-unit spikes, snap to the 100 us grid, write with spikepack.write_blosc",
                "write metadata parquet, schema.yaml, provenance.yaml, manifest.json, SUMMARY.md",
            ],
            "tools": {"spikepack": spikepack.__version__ + " @ 30ab06ff7794d89cab17cb54338db869ad90d036",
                      "ibl-ai-agent": git_head(), "python": sys.version.split()[0]},
            "lossy": ["spike times snapped to the 100 us grid (max shift 50 us) before shard encoding"],
            "dropped": ["spikes of units with label < 1", "spike amplitudes, depths, templates and waveforms",
                        "trials.intervals_bpod, quiescencePeriod, stimOnTrigger_times, stimOffTrigger_times",
                        "passive-protocol data", "LFP, raw ephys, video, wheel, pose, licks and motion energy (referenced in place)"]
                       + [f"trials column absent upstream: {c}" for c in trials_skipped],
        },
        "source_selection_rule": SOURCE_SELECTION_RULE,
        "trials_probabilityLeft_written": biased,
        "conversion_failures": failures,
        "build_seconds": round(seconds, 1),
        "ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ingested_by": "Claude Code (data-ingest skill v0) for the IBL aging ingestion pilot",
    }
    (out_dir / "provenance.yaml").write_text(yaml.safe_dump(provenance, sort_keys=False, width=100))

    t = tables
    summary = [f"# {DATASET_NAME} {DATASET_VERSION}: generated counts", "",
               f"- subjects: {len(t['subjects'])}", f"- sessions: {len(t['sessions'])}",
               f"- recordings (probes): {len(t['recordings'])}, with spikes: {int(t['recordings'].has_spikes.sum())}",
               f"- good units: {len(t['units'])}", f"- trials: {len(t['trials'])}", f"- events: {len(t['events'])}",
               f"- channels: {len(t['channels'])}", f"- epochs: {len(t['epochs'])} (no epoch sets defined)",
               f"- spike shards: {len(list((out_dir / 'spikes').glob('*/meta.json')))}",
               f"- conversion failures: {len(failures)}", ""]
    (out_dir / "SUMMARY.md").write_text("\n".join(summary))

    files = []
    for p in sorted(out_dir.rglob("*")):
        if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts:
            files.append({"path": str(p.relative_to(out_dir)), "bytes": p.stat().st_size,
                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    (out_dir / "manifest.json").write_text(json.dumps({"dataset_name": DATASET_NAME, "dataset_version": DATASET_VERSION,
                                                       "files": files}, indent=1))


def git_head():
    import subprocess
    out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO_DIR)
    return out.stdout.strip() or "unknown"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=1, help="processes converting probes in parallel")
    build(PACKAGE_DIR, workers=parser.parse_args().workers)

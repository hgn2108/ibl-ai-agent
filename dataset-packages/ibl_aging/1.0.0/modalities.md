# Modalities

## Spikes (Neuropixels, sorted)
### Instrument
Neuropixels probes, by Alyx model code: 3B2 (590), 3A (173), NP2.4 (4). The per-probe model is in `recordings.probe_model`.
### Sampling
Spike times from the AP band, stored on a 100 µs grid.
### Units
Seconds.
### Preprocessing
Spike sorting uses the sorter in `recordings.sorter`:
- 699 BWM probes: collection `pykilosort`, ALF revision `2024-05-06` (release
  `2024_Q2_IBL_et_al_BWM_iblsort`); the sorter log says Pykilosort version 1.7.0.
- 64 extra probes: collection `iblsorter`, unrevisioned (release `2025_Q3_Zang_et_al_Aging`);
  Alyx records iblsorter 1.9.1 (46), 1.9.0a (2) or only `3.2.0` (16, sorter version unknown).
- The paper says all probes used one version; the data disagrees. See `scientific-context.md`.
- 4 extra probes: no sorting exists upstream, so `has_spikes = false`.

Only units with `clusters.metrics label == 1` (all three IBL single-unit metrics pass)
are kept. Each spike time is snapped to the 100 µs grid before encoding, which moves it
by at most 50 µs.
### Time base
`session_clock`: ibllib's ephys sync upstream puts spike times on the session main clock.
### Coverage
763 of 767 probes have spikes. Region labels come from histology-aligned channel
locations (`units.acronym`, `units.beryl_acronym`).
### QC
Alyx insertion QC is in `recordings.alyx_qc`. Unit metrics are in `units` (firing rate,
amplitude, presence ratio, contamination, drift, sliding RP, noise cutoff).

## Behaviour (trials and events)
### Instrument
iblrig / Bpod and the wheel.
### Sampling
One row per trial (`trials`) and one row per trial event (`events`).
### Units
Seconds for times, dimensionless for contrast and `probabilityLeft`, µL for
`rewardVolume`.
### Preprocessing
ibllib trial extraction upstream. The default tagged trials revision is used; it is
recorded per session in `sessions.trials_revision`.
### Time base
`session_clock`: trials are synchronised upstream to the ephys main clock.
### Coverage
All 497 sessions.
### QC
No trial inclusion mask is shipped. 105 trials in 30 sessions have no `stimOn_times` (NaN).
The `epochs` table exists but is empty: no epoch sets are defined, and passive-protocol
epochs are not carried.

## LFP (referenced in place)
### Instrument
Neuropixels LF band.
### Sampling
Declared in each file's `.lf.meta`.
### Units
Volts after the gain in `.meta` is applied.
### Preprocessing
None.
### Time base
Sample clock of the probe. It maps to `session_clock` through `*.sync.npy` /
`*.timestamps.npy`.
### Coverage
Per probe on OpenAlyx; see `schema.yaml` `stores.lfp.resolve`.
### QC
`_iblqc_ephys*` datasets upstream.

## Video, pose, wheel, licks (referenced in place)
### Instrument
Left, right and body cameras, and the wheel. How licks are detected is not stated.
### Sampling
Camera frame times are in `_ibl_<cam>Camera.times.npy`.
### Units
Seconds for times, pixels for pose, radians for wheel position, a.u. for motion energy.
### Preprocessing
DLC pose was present in both sessions checked. Lightning Pose was also present in the BWM
session checked.
### Time base
`session_clock`.
### Coverage
Per session on OpenAlyx; see `schema.yaml` `stores`.
### QC
Not carried.

"""Compute ground-truth answers for the three behaviour eval questions.

Run from the repo root:

    UV_CACHE_DIR=.uv-cache uv run --no-sync python tests/evals/behaviour/compute_ground_truth.py

Reads the local `bwm_behavior` dataset (resolved through data_locations) and
writes `ground_truth.json` next to this file. The eval grid grades model answers
against that file, so every number a model is scored on is derived here, in
code a scientist can read and re-run.

Each question below states the exact inclusion rule it assumes. Those rules are
the definition of the question: a different rule gives a different correct
answer, so they are also quoted in the question text shown to the models.
"""

import json
from pathlib import Path

import pandas as pd

from ibl_ai_agent.data_locations import resolve_dataset_dir

OUT_PATH = Path(__file__).parent / "ground_truth.json"


def load_tables():
    """Return (trials, pose_availability, sessions) from the local bwm_behavior dataset.

    trials: one row per trial (295,920), pose_availability: one row per
    session x camera (1,144), sessions: one row per session (459).
    """
    root = resolve_dataset_dir("bwm_behavior")
    trials = pd.read_parquet(root / "metadata/trials.parquet")
    pose = pd.read_parquet(root / "metadata/pose_availability.parquet")
    sessions = pd.read_parquet(root / "metadata/sessions.parquet")
    return trials, pose, sessions


def q1_pose_coverage(pose, sessions):
    """Q1: pose-data coverage, broken down by camera and pose tracker.

    Coverage is counted from pose_availability rows with pose_present, because
    a session can have pose on some cameras but not others. The tracker column
    matters: the dataset mixes Lightning Pose and DeepLabCut, so a session count
    alone hides which tracker produced the keypoints.
    """
    present = pose[pose.pose_present]
    by_camera_tracker = (
        present.groupby(["camera", "tracker"]).eid.nunique().unstack(fill_value=0)
    )
    return {
        "n_sessions_total": int(len(sessions)),
        "n_sessions_with_any_pose": int(present.eid.nunique()),
        "sessions_by_camera_and_tracker": {
            camera: row.to_dict() for camera, row in by_camera_tracker.iterrows()
        },
        "n_sessions_by_camera": present.groupby("camera").eid.nunique().to_dict(),
    }


def q2_zero_contrast_performance(trials):
    """Q2: proportion correct on zero-contrast trials, split by block prior.

    Zero-contrast trials are those where the presented side carried 0% contrast:
    the mouse cannot see which side is correct, so performance above 0.5 reflects
    use of the block prior rather than the stimulus. The unpresented side is NaN,
    so the two contrast columns are combined before testing for zero.

    No-go trials (choice == 0, 247 trials) are excluded: the mouse made no
    report, so the trial measures neither perception nor prior. Correctness is
    read from feedbackType (+1 rewarded, -1 error).
    """
    is_zero_contrast = (trials.contrastLeft.fillna(-1) == 0) | (
        trials.contrastRight.fillna(-1) == 0
    )
    zero = trials[is_zero_contrast & (trials.choice != 0)]
    by_block = zero.groupby("probabilityLeft").apply(
        lambda g: (g.feedbackType == 1).mean(), include_groups=False
    )
    return {
        "n_trials": int(len(zero)),
        "proportion_correct_overall": float((zero.feedbackType == 1).mean()),
        "proportion_correct_by_probability_left": {
            str(prior): float(value) for prior, value in by_block.items()
        },
        "n_trials_by_probability_left": {
            str(prior): int(count) for prior, count in zero.probabilityLeft.value_counts().items()
        },
    }


def q3_premovement_trials(trials):
    """Q3: trials whose first wheel movement precedes stimulus onset, dataset-wide.

    These trials are excluded from stimulus-locked analyses, because movement
    activity swamps the sensory response -- so this fraction is the share of the
    dataset lost to that filter.

    firstMovement_times is NaN when no movement was detected in the trial. NaN
    comparisons are False in pandas, so those trials are excluded automatically
    rather than counted as early movements -- the failure mode this question is
    designed to expose.

    Pooled over all trials (one denominator), not the mean of per-session
    fractions; the two differ and the question text says which is wanted.
    """
    moved_before_stimulus = trials.firstMovement_times < trials.stimOn_times
    return {
        "n_trials_total": int(len(trials)),
        "n_trials_movement_before_stimulus": int(moved_before_stimulus.sum()),
        "fraction_trials_movement_before_stimulus": float(moved_before_stimulus.mean()),
        "n_trials_no_movement_recorded": int(trials.firstMovement_times.isna().sum()),
    }


if __name__ == "__main__":
    trials, pose, sessions = load_tables()
    ground_truth = {
        "dataset": "bwm_behavior 2.0.0",
        "q1_pose_coverage": q1_pose_coverage(pose, sessions),
        "q2_zero_contrast_performance": q2_zero_contrast_performance(trials),
        "q3_premovement_trials": q3_premovement_trials(trials),
    }
    OUT_PATH.write_text(json.dumps(ground_truth, indent=2))
    print(json.dumps(ground_truth, indent=2))
    print(f"\nwrote {OUT_PATH}")

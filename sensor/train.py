"""Rebuild the sensor models from scratch: python -m sensor.train

Writes two model files to sensor/models/:
  demo (default for predict): trained on loads 0/1/2 only; load 3 (1730 rpm) is the honest demo set
  all  (SENSOR_MODEL=all):    trained on all 40 recordings; every demo prediction is in-sample
"""
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from .data_loading import RECORDINGS, load_recording, windows
from .features import FEATURE_NAMES, VARIANTS, envelope_peaks, extract

SEED = 42
FINAL_VARIANT = "+envelope"  # set ONLY from inner-CV selection (python -m sensor.evaluate --compare), never test folds
DEMO_TEST_LOAD = 3
MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATHS = {v: MODEL_DIR / f"sensor_model_{v}.joblib" for v in ("demo", "all")}


def build_dataset(recording_ids=RECORDINGS):
    """All windows of the given recordings -> X, fault_type, severity, recording id, load_hp (per window)."""
    parts = []
    for rid in recording_ids:
        sig, rpm = load_recording(rid)
        X = extract(windows(sig), rpm)
        meta = RECORDINGS[rid]
        parts.append((X, [meta["fault_type"]] * len(X), [meta["severity"]] * len(X), [rid] * len(X), [meta["load_hp"]] * len(X)))
    return [np.concatenate(p) for p in zip(*parts)]


def make_model():
    # ponytail: fixed hyperparameters, no tuning yet; any tuning must use inner grouped CV on train loads only
    return RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=SEED, n_jobs=-1)


def cols(variant):
    return [FEATURE_NAMES.index(f) for f in VARIANTS[variant]]


def fit(X, y_type, y_sev, variant=FINAL_VARIANT):
    """X has all FEATURE_NAMES columns; the model uses (and remembers) the variant's subset."""
    c = cols(variant)
    faulty = y_type != "normal"
    return {"fault_type": make_model().fit(X[:, c], y_type), "severity": make_model().fit(X[faulty][:, c], y_sev[faulty]),
            "variant": variant, "cols": c}


def normal_env_p99(loads):
    """Healthy baseline for evidence(): 99th percentile, per fault frequency/harmonic, of the envelope peak/median
    ratio over all Normal windows at the given loads."""
    ratios = []
    for hp in loads:
        sig, rpm = load_recording(f"Normal_{hp}")
        ratios.append(envelope_peaks(windows(sig), rpm)[0])
    return np.percentile(np.concatenate(ratios), 99, axis=0)


def train_all():
    """Train and save both model files (demo default, all)."""
    X, y_type, y_sev, rec, load = build_dataset()
    print("dataset:", X.shape, dict(zip(*np.unique(y_type, return_counts=True))))
    MODEL_DIR.mkdir(exist_ok=True)
    for variant, keep in [("demo", load != DEMO_TEST_LOAD), ("all", np.ones(len(X), bool))]:
        m = fit(X[keep], y_type[keep], y_sev[keep])
        m["normal_env_p99"] = normal_env_p99(sorted(set(load[keep])))
        joblib.dump(m, MODEL_PATHS[variant], compress=3)
        print(f"saved {variant}: {keep.sum()} windows -> {MODEL_PATHS[variant]} ({MODEL_PATHS[variant].stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    train_all()

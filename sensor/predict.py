"""Handover interface for Kushal's service.

    from sensor.predict import predict, list_recordings, get_window
    predict("OR007@6_0", 12)  -> sensor result dict (data contract shape)

Mock mode (team MOCK_MODE=true from .env.example, or SENSOR_MOCK=1) returns the contract sample without data or models.
SENSOR_MODEL=demo (default) uses the model trained on loads 0/1/2: demo from recordings with held_out=True.
SENSOR_MODEL=all uses the model trained on all 40 recordings (every prediction in-sample).
"""
import json
import os
import sys
from functools import lru_cache

import joblib
import numpy as np

from . import mock
from .data_loading import LOADS, RECORDINGS, SAMPLE_RATE_HZ, load_recording, n_windows, window_slice
from .features import ENV_FAULTS, FAULT_MULT as FAULT_HZ, HARMONICS, envelope_peaks, extract
from .config import EVIDENCE_MIN_VS_NORMAL, HIGH_UNCERTAINTY_BELOW, evidence_strength
from .train import DEMO_TEST_LOAD, MODEL_PATHS

FAULT_TYPES = ["normal", "inner_race", "outer_race", "ball"]
MOCK = os.environ.get("SENSOR_MOCK") == "1" or os.environ.get("MOCK_MODE", "").lower() == "true"
MODEL_VARIANT = os.environ.get("SENSOR_MODEL", "demo")


@lru_cache(maxsize=1)
def _models():
    return joblib.load(MODEL_PATHS[MODEL_VARIANT])


def predict(recording_id, window_index):
    if MOCK:
        return mock.predict(recording_id, window_index)
    sig, rpm = load_recording(recording_id)
    m = _models()
    w = window_slice(sig, window_index)
    feats = extract(w, rpm)[:, m["cols"]]
    proba = dict(zip(m["fault_type"].classes_, m["fault_type"].predict_proba(feats)[0]))
    fault_type = str(max(proba, key=proba.get))  # plain str, not numpy.str_
    severity = "none" if fault_type == "normal" else str(m["severity"].predict(feats)[0])
    return {
        "recording_id": recording_id,
        "window_index": int(window_index),
        "fault_type": fault_type,
        "severity": severity,
        "confidence": round(float(proba[fault_type]), 4),
        "probabilities": {k: round(float(proba[k]), 4) for k in FAULT_TYPES},
        "context": {"sensor": "drive_end", "sample_rate_hz": SAMPLE_RATE_HZ,
                    "load_hp": RECORDINGS[recording_id]["load_hp"], "rpm": round(rpm)},
        "evidence": window_evidence(w, rpm, m["normal_env_p99"]),  # optional field; missing == []
    }


def window_evidence(window, rpm, normal_env_p99, min_vs_normal=EVIDENCE_MIN_VS_NORMAL):
    """Envelope-spectrum peaks at BPFI/BPFO/BSF x1-3 (from the actual rpm) that stand out vs the healthy baseline.
    vs_normal = (peak / median of the envelope spectrum 0-1000 Hz) / (99th percentile of that same ratio over the
    healthy windows the model trained on). Entries below min_vs_normal are dropped, and a harmonic (2x, 3x) only
    counts if its family's fundamental (1x) passes too: BPFI 2x and BPFO 3x share a band near 310 Hz.
    Strongest first; [] if none."""
    ratios, peak_hz = envelope_peaks(np.asarray(window)[None], rpm)
    names = [(k, h) for k in ENV_FAULTS for h in HARMONICS]
    vs_all = {name: round(float(ratios[0, j] / normal_env_p99[j]), 2) for j, name in enumerate(names)}
    out = []
    for j, (k, h) in enumerate(names):
        vs = vs_all[(k, h)]
        if vs >= min_vs_normal and vs_all[(k, 1)] >= min_vs_normal:
            out.append({"feature": "envelope_peak", "freq_hz": round(float(peak_hz[0, j]), 1),
                        "expected_hz": round(FAULT_HZ[k] * h * rpm / 60, 1), "matches": k.upper(), "harmonic": h,
                        "vs_normal": vs, "strength": evidence_strength(vs)})
    return sorted(out, key=lambda e: -e["vs_normal"])


def evidence(recording_id, window_index):
    """Physics facts behind a window (the optional "evidence" field). Independent of the classifier."""
    sig, rpm = load_recording(recording_id)
    return window_evidence(window_slice(sig, window_index), rpm, _models()["normal_env_p99"])


def is_uncertain(result):
    """True when uncertainty_level(confidence) is "high" (confidence below HIGH_UNCERTAINTY_BELOW)."""
    return result["confidence"] < HIGH_UNCERTAINTY_BELOW


def list_recordings():
    out = []
    for rid, meta in RECORDINGS.items():
        if MOCK:
            rpm, nw = LOADS[meta["load_hp"]], 117
        else:
            sig, rpm = load_recording(rid)
            nw = n_windows(len(sig))
        out.append({"recording_id": rid, "load_hp": meta["load_hp"], "rpm": round(rpm),
                    "fault_type": meta["fault_type"], "severity": meta["severity"], "n_windows": nw,
                    "held_out": MODEL_VARIANT == "demo" and meta["load_hp"] == DEMO_TEST_LOAD})
    return out


def get_window(recording_id, window_index, max_points=None):
    """Window samples for the chart. max_points (GET /signal) keeps every k-th sample so len <= max_points;
    sample_rate_hz is then the rate of the returned list (12000 / k), so i / sample_rate_hz stays the true time."""
    if MOCK:
        out = mock.get_window(recording_id, window_index)
    else:
        sig, _ = load_recording(recording_id)
        out = {"samples": window_slice(sig, window_index).tolist(), "sample_rate_hz": SAMPLE_RATE_HZ}
    if max_points and len(out["samples"]) > max_points:
        # ponytail: plain decimation, can drop single-sample impact spikes; min/max buckets if the chart needs them
        k = -(-len(out["samples"]) // max_points)
        out = {"samples": out["samples"][::k], "sample_rate_hz": out["sample_rate_hz"] / k}
    return out


if __name__ == "__main__":
    rid, idx = (sys.argv[1], int(sys.argv[2])) if len(sys.argv) > 2 else ("OR007@6_0", 12)
    print(json.dumps(predict(rid, idx), indent=2))

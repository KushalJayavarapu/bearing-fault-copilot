"""Mock sensor result (exact sample from the data contract). Enabled with SENSOR_MOCK=1."""
import copy

import numpy as np

SAMPLE = {
    "recording_id": "OR007@6_0",
    "window_index": 12,
    "fault_type": "outer_race",
    "severity": "small",
    "confidence": 0.93,
    "probabilities": {"normal": 0.01, "inner_race": 0.02, "outer_race": 0.93, "ball": 0.04},
    "context": {"sensor": "drive_end", "sample_rate_hz": 12000, "load_hp": 0, "rpm": 1797},
    # real evidence() output for OR007@6_0 window 12 (strongest entry)
    "evidence": [{"feature": "envelope_peak", "freq_hz": 105.5, "expected_hz": 107.3, "matches": "BPFO", "harmonic": 1,
                  "vs_normal": 5.93, "strength": "high"}],
}


def predict(recording_id=None, window_index=None):
    return copy.deepcopy(SAMPLE)


def get_window(recording_id=None, window_index=None):
    # fake vibration: 107 Hz tone (BPFO at 1797 rpm) + noise, deterministic
    t = np.arange(2048) / 12000
    x = 0.1 * np.sin(2 * np.pi * 107.4 * t) + 0.05 * np.random.default_rng(0).standard_normal(2048)
    return {"samples": x.round(5).tolist(), "sample_rate_hz": 12000}

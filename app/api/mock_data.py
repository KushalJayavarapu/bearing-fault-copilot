"""Canned data for MOCK_MODE.

Pure Python (no numpy, scipy or scikit-learn), so the mock API runs with only FastAPI installed.
The 40 recording ids mirror sensor/data_loading.py; test_api.py checks they stay in sync.
Everything is deterministic: the same recording and window always give the same answer.
All text and numbers are placeholders for UI work and are labeled "[MOCK]" so they cannot pass for a real analysis.
"""
import copy
import hashlib
import math
import random

from . import uncertainty

MOCK_TAG = "[MOCK] "
N_WINDOWS = 117  # same value sensor.predict.list_recordings() uses in mock mode
HELD_OUT_LOAD = 3  # the demo recordings the real model never trained on
SAMPLE_RATE_HZ = 12000
WINDOW = 2048
LOADS = {0: 1797, 1: 1772, 2: 1750, 3: 1730}  # hp -> rpm
FAULT_TYPES = ["normal", "inner_race", "outer_race", "ball"]
# fault frequency = multiplier x shaft speed in Hz (published CWRU drive-end bearing values)
FAULT_HZ = {"inner_race": ("BPFI", 5.4152), "outer_race": ("BPFO", 3.5848), "ball": ("BSF", 4.7135)}

# (id prefix, fault_type, severity)
CONDITIONS = [
    ("Normal", "normal", "none"),
    ("IR007", "inner_race", "small"),
    ("IR014", "inner_race", "medium"),
    ("IR021", "inner_race", "large"),
    ("B007", "ball", "small"),
    ("B014", "ball", "medium"),
    ("B021", "ball", "large"),
    ("OR007@6", "outer_race", "small"),
    ("OR014@6", "outer_race", "medium"),
    ("OR021@6", "outer_race", "large"),
]
RECORDINGS = {
    f"{prefix}_{hp}": {"fault_type": ft, "severity": sev, "load_hp": hp}
    for prefix, ft, sev in CONDITIONS
    for hp in LOADS
}

# The exact sample from docs/contract.md section 1. Returned for (OR007@6_0, window 12).
CONTRACT_SENSOR_SAMPLE = {
    "recording_id": "OR007@6_0",
    "window_index": 12,
    "fault_type": "outer_race",
    "severity": "small",
    "confidence": 0.93,
    "probabilities": {"normal": 0.01, "inner_race": 0.02, "outer_race": 0.93, "ball": 0.04},
    "context": {"sensor": "drive_end", "sample_rate_hz": 12000, "load_hp": 0, "rpm": 1797},
}
GOLDEN = ("OR007@6_0", 12)


def list_recordings():
    return [{"recording_id": rid, "load_hp": r["load_hp"], "rpm": LOADS[r["load_hp"]],
             "fault_type": r["fault_type"], "severity": r["severity"], "n_windows": N_WINDOWS,
             "held_out": r["load_hp"] == HELD_OUT_LOAD} for rid, r in RECORDINGS.items()]


def window(rid, idx, max_points=None):
    """Fake vibration: noise + shaft rotation + a tone at the fault frequency (louder for bigger faults).
    max_points keeps every k-th sample; sample_rate_hz is then the rate of the returned list."""
    rec = RECORDINGS[rid]
    rpm = LOADS[rec["load_hp"]]
    rng = random.Random(f"{rid}:{idx}")
    amp = {"none": 0.0, "small": 0.10, "medium": 0.16, "large": 0.24}[rec["severity"]]
    fault_hz = FAULT_HZ[rec["fault_type"]][1] * rpm / 60 if amp else 0.0
    samples = []
    for i in range(WINDOW):
        t = i / SAMPLE_RATE_HZ
        x = 0.05 * rng.gauss(0, 1) + 0.03 * math.sin(2 * math.pi * rpm / 60 * t)
        if amp:
            x += amp * math.sin(2 * math.pi * fault_hz * t)
        samples.append(round(x, 5))
    rate = SAMPLE_RATE_HZ
    if max_points and len(samples) > max_points:
        k = -(-len(samples) // max_points)
        samples, rate = samples[::k], SAMPLE_RATE_HZ / k
    return {"samples": samples, "sample_rate_hz": rate}


def _unit(salt, rid, idx):
    """Stable pseudo-random number in [0, 1) (hashlib, not hash(), which changes between runs)."""
    d = hashlib.sha256(f"{salt}:{rid}:{idx}".encode()).digest()
    return int.from_bytes(d[:4], "big") / 2**32


def _evidence(rec):
    ft = rec["fault_type"]
    if ft == "normal":
        return []
    name, mult = FAULT_HZ[ft]
    expected = round(mult * LOADS[rec["load_hp"]] / 60, 1)
    ratio = 1.2 if ft == "ball" else {"small": 6.14, "medium": 4.2, "large": 3.3}[rec["severity"]]
    strength = "high" if ratio >= 3 else "medium" if ratio >= 1.5 else "low"
    return [{"feature": "envelope_peak", "freq_hz": round(expected + 1.5, 1), "expected_hz": expected,
             "matches": name, "harmonic": 1, "vs_normal": ratio, "strength": strength}]


def sensor_result(rid, idx):
    """Mock classifier output: always the true label, with a confidence that sweeps all three uncertainty
    levels across windows (about 20% high, 40% medium, 40% low) so the screen can show every state."""
    rec = RECORDINGS[rid]
    ft = rec["fault_type"]
    if (rid, idx) == GOLDEN:
        res = copy.deepcopy(CONTRACT_SENSOR_SAMPLE)
    else:
        band, u = _unit("band", rid, idx), _unit("conf", rid, idx)
        conf = 0.45 + 0.14 * u if band < 0.2 else 0.62 + 0.32 * u if band < 0.6 else 0.95 + 0.04 * u
        conf = round(conf, 2)
        others = [c for c in FAULT_TYPES if c != ft]
        second = others.pop(int(_unit("second", rid, idx) * 3))
        rest = 1 - conf
        p2, p3 = round(rest * 0.6, 2), round(rest * 0.25, 2)
        probs = {ft: conf, second: p2, others[0]: p3, others[1]: max(0.0, round(1 - conf - p2 - p3, 2))}
        res = {"recording_id": rid, "window_index": idx, "fault_type": ft,
               "severity": "none" if ft == "normal" else rec["severity"], "confidence": conf,
               "probabilities": {c: probs[c] for c in FAULT_TYPES},
               "context": {"sensor": "drive_end", "sample_rate_hz": SAMPLE_RATE_HZ,
                           "load_hp": rec["load_hp"], "rpm": LOADS[rec["load_hp"]]}}
    res["evidence"] = _evidence(rec)
    return res


def _cite(fault, n):
    return {"id": f"mock-{fault}-{n}", "source_title": "[MOCK] Placeholder bearing guide", "page": n,
            "url": "https://example.com/mock",
            "excerpt": "Placeholder text for UI work. This is not from a real document."}


CONTENT = {
    "normal": {
        "explanation": "No bearing fault pattern was found in this window. The vibration looks like a healthy bearing at this load.",
        "causes": [],
        "actions": [{"step": "Keep routine condition monitoring. No action is needed now.",
                     "safety_critical": False, "citation_ids": ["mock-normal-1"]}],
        "citations": [_cite("normal", 1)],
    },
    "inner_race": {
        "explanation": "The vibration pattern points to a defect on the inner race (the ring that sits on the shaft), size {severity}. Repeating impacts at the inner-race fault frequency stand out in the signal.",
        "causes": ["Fatigue wear (spalling) on the inner ring", "Shaft overload or too tight a fit on the shaft",
                   "Poor lubrication or contamination"],
        "actions": [
            {"step": "Stop the machine and lock out the power before opening the bearing housing.",
             "safety_critical": True, "citation_ids": ["mock-inner_race-1"]},
            {"step": "Inspect the inner ring raceway and the shaft seat for spalling, pitting or fretting.",
             "safety_critical": True, "citation_ids": ["mock-inner_race-1"]},
            {"step": "Check the shaft fit, the lubricant condition and the load on the bearing.",
             "safety_critical": False, "citation_ids": ["mock-inner_race-2"]},
            {"step": "Plan a bearing replacement at the next maintenance window if damage is confirmed.",
             "safety_critical": False, "citation_ids": ["mock-inner_race-2"]},
        ],
        "citations": [_cite("inner_race", 1), _cite("inner_race", 2)],
    },
    "outer_race": {
        "explanation": "The vibration pattern points to a defect on the outer race (the fixed outer ring), size {severity}. A repeating impact at the outer-race fault frequency stands out in the signal.",
        "causes": ["Fatigue wear (spalling) on the outer ring", "Misalignment or uneven load on the bearing",
                   "Poor lubrication or contamination", "Incorrect fit in the housing"],
        "actions": [
            {"step": "Stop the machine and lock out the power before opening the bearing housing.",
             "safety_critical": True, "citation_ids": ["mock-outer_race-1"]},
            {"step": "Inspect the outer ring raceway for spalling or pitting and check the housing fit.",
             "safety_critical": True, "citation_ids": ["mock-outer_race-1"]},
            {"step": "Check the lubricant level and condition, and the shaft alignment.",
             "safety_critical": False, "citation_ids": ["mock-outer_race-2"]},
            {"step": "Plan a bearing replacement at the next maintenance window if damage is confirmed.",
             "safety_critical": False, "citation_ids": ["mock-outer_race-2"]},
        ],
        "citations": [_cite("outer_race", 1), _cite("outer_race", 2)],
    },
    "ball": {
        "explanation": "The pattern suggests damage to the rolling elements (the balls), size {severity}. Ball faults are the hardest to confirm from vibration alone, so inspect before acting.",
        "causes": ["Wear or pitting of the balls", "Contamination in the lubricant", "Overload or shock loading"],
        "actions": [
            {"step": "Stop the machine and lock out the power before opening the bearing housing.",
             "safety_critical": True, "citation_ids": ["mock-ball-1"]},
            {"step": "Inspect the balls and the cage for wear, pitting or discoloration.",
             "safety_critical": True, "citation_ids": ["mock-ball-1"]},
            {"step": "Check the lubricant for contamination and review recent shock loads.",
             "safety_critical": False, "citation_ids": ["mock-ball-2"]},
        ],
        "citations": [_cite("ball", 1), _cite("ball", 2)],
    },
}
HEDGE = "The classifier is not sure about this window, so treat what follows as a possibility, not a finding. "
NOTES = {
    "high": "Low confidence ({pct}%). Treat this label as a hint only and arrange a manual inspection.",
    "medium": "Moderate confidence ({pct}%). Confirm with a manual check before acting.",
    "low": "High confidence ({pct}%) on lab-trained data. Confirm before acting on safety-critical steps.",
}


def analyze(rid, idx):
    """The final answer (contract section 3) without request_id."""
    sensor = sensor_result(rid, idx)
    conf, sev = sensor["confidence"], sensor["severity"]
    content = CONTENT[sensor["fault_type"]]
    level = uncertainty.level(conf)
    actions = copy.deepcopy(content["actions"])
    explanation = content["explanation"].format(severity=sev)
    if level == "high":
        explanation = HEDGE + explanation
        actions.insert(0, {"step": "Arrange a manual inspection before relying on this result.",
                           "safety_critical": False, "citation_ids": []})
    return {
        "sensor": sensor,
        "explanation": MOCK_TAG + explanation,
        "likely_causes": list(content["causes"]),
        "recommended_actions": actions,
        "needs_human_confirm": level == "high" or any(a["safety_critical"] for a in actions),
        "citations": copy.deepcopy(content["citations"]),
        "uncertainty": {"level": level, "note": NOTES[level].format(pct=round(conf * 100))},
        "meta": {"model": "mock", "served_on": "mock (no AMD GPU used)",
                 "latency_ms": {"classifier": 84, "retrieval": 120, "llm": 1800, "total": 2004}},
    }

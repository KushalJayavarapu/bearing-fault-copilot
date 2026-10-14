"""Self-check: python -m sensor.test_sensor   (needs data + models; mock part always runs)"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

MOCK_CHECK = """
from sensor.predict import predict, list_recordings, get_window
from sensor.mock import SAMPLE
assert predict('anything', 0) == SAMPLE and len(SAMPLE['evidence']) == 1
assert len(list_recordings()) == 40 and len(get_window('x', 0)['samples']) == 2048
w = get_window('x', 0, max_points=500)
assert len(w['samples']) <= 500 and w['sample_rate_hz'] == 12000 / 5
"""
EVIDENCE_KEYS = {"feature", "freq_hz", "expected_hz", "matches", "harmonic", "vs_normal", "strength"}


def check_evidence(ev):
    from .config import EVIDENCE_HIGH_VS_NORMAL, EVIDENCE_MIN_VS_NORMAL
    assert isinstance(ev, list)
    assert [e["vs_normal"] for e in ev] == sorted((e["vs_normal"] for e in ev), reverse=True)
    for e in ev:
        assert set(e) == EVIDENCE_KEYS, e
        assert e["feature"] == "envelope_peak" and e["matches"] in ("BPFI", "BPFO", "BSF", "FTF") and e["harmonic"] in (1, 2, 3)
        assert all(type(e[k]) is float for k in ("freq_hz", "expected_hz", "vs_normal")) and type(e["harmonic"]) is int
        assert abs(e["freq_hz"] - e["expected_hz"]) <= 0.05 * e["expected_hz"] + 5.9  # within the +-5% band (+1 bin)
        assert e["vs_normal"] >= EVIDENCE_MIN_VS_NORMAL
        assert e["strength"] == ("high" if e["vs_normal"] >= EVIDENCE_HIGH_VS_NORMAL else "medium")
        if e["harmonic"] > 1:
            assert any(f["matches"] == e["matches"] and f["harmonic"] == 1 for f in ev)


if __name__ == "__main__":
    for flag in ({"SENSOR_MOCK": "1"}, {"MOCK_MODE": "true"}):  # either switch turns mock on; no data, no model
        env = os.environ | flag | {"SENSOR_DATA_DIR": "/nonexistent"}
        subprocess.run([sys.executable, "-c", MOCK_CHECK], check=True, env=env)
        print("mock ok with", flag)

    from .mock import SAMPLE
    contract = Path(__file__).resolve().parent.parent / "docs" / "contract.md"
    section1 = re.search(r"## 1\. Sensor result(.*?)\n## 2\.", contract.read_text(encoding="utf-8"), re.S).group(1)
    sample, example = (json.loads(b) for b in re.findall(r"```json\n(.*?)```", section1, re.S))
    assert {k: v for k, v in SAMPLE.items() if k != "evidence"} == sample, "mock differs from the section 1 sample"
    assert {"evidence": SAMPLE["evidence"]} == example, "mock evidence differs from the section 1 evidence example"
    check_evidence(SAMPLE["evidence"])
    print("mock == docs/contract.md section 1 sample + evidence example")

    from .data_loading import ALL_FILES, DATA_DIR, MANIFEST, RECORDINGS, verify
    assert {m["file"] for m in ALL_FILES.values()} == set(MANIFEST)
    assert all(verify(DATA_DIR / f"{m['file']}.mat", m["file"]) is None for m in RECORDINGS.values())
    print("40 recordings match cwru_manifest.json")

    from .predict import evidence, get_window, list_recordings, predict
    recs = list_recordings()
    held = [r for r in recs if r["held_out"]]
    assert len(held) == 10 and all(r["load_hp"] == 3 for r in held)
    t0 = time.perf_counter()
    r = predict("IR021_3", 40)
    cold = time.perf_counter() - t0
    assert list(r) == list(SAMPLE) and list(r["context"]) == list(SAMPLE["context"])
    assert list(r["probabilities"]) == ["normal", "inner_race", "outer_race", "ball"]
    assert (r["severity"] == "none") == (r["fault_type"] == "normal")
    assert all(type(r[k]) is str for k in ("recording_id", "fault_type", "severity")) and type(r["window_index"]) is int
    check_evidence(r["evidence"])
    assert r["evidence"] == evidence("IR021_3", 40) and r["evidence"][0]["matches"] == "BPFI"
    assert predict("OR007@6_3", 58)["evidence"][0]["matches"] == "BPFO"
    normal = next(x for x in recs if x["recording_id"] == "Normal_3")
    for i in range(0, normal["n_windows"], 10):  # healthy windows: always []
        assert predict("Normal_3", i)["evidence"] == []
    w = get_window("IR021_3", 40, max_points=512)
    assert len(w["samples"]) == 512 and w["sample_rate_hz"] == 3000 and get_window("IR021_3", 40)["samples"][::4] == w["samples"]
    t = []
    for i in range(20):
        t0 = time.perf_counter()
        predict("OR021@6_3", i)
        t.append(time.perf_counter() - t0)
    print(f"interface ok; cold predict {cold * 1000:.0f} ms, warm median {sorted(t)[10] * 1000:.0f} ms, max {max(t) * 1000:.0f} ms")

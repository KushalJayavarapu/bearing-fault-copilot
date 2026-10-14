"""Self-check: python -m sensor.test_sensor   (needs data + models; mock part always runs)"""
import os
import subprocess
import sys
import time

MOCK_CHECK = """
from sensor.predict import predict, list_recordings, get_window
from sensor.mock import SAMPLE
assert predict('anything', 0) == SAMPLE
assert len(list_recordings()) == 40 and len(get_window('x', 0)['samples']) == 2048
w = get_window('x', 0, max_points=500)
assert len(w['samples']) <= 500 and w['sample_rate_hz'] == 12000 / 5
"""

if __name__ == "__main__":
    for flag in ({"SENSOR_MOCK": "1"}, {"MOCK_MODE": "true"}):  # either switch turns mock on; no data, no model
        env = os.environ | flag | {"SENSOR_DATA_DIR": "/nonexistent"}
        subprocess.run([sys.executable, "-c", MOCK_CHECK], check=True, env=env)
        print("mock ok with", flag)

    from .mock import SAMPLE
    from .predict import evidence, get_window, list_recordings, predict
    recs = list_recordings()
    held = [r for r in recs if r["held_out"]]
    assert len(held) == 10 and all(r["load_hp"] == 3 for r in held)
    t0 = time.perf_counter()
    r = predict("IR021_3", 40)
    cold = time.perf_counter() - t0
    assert set(r) == set(SAMPLE) and set(r["context"]) == set(SAMPLE["context"])
    assert list(r["probabilities"]) == ["normal", "inner_race", "outer_race", "ball"]
    assert (r["severity"] == "none") == (r["fault_type"] == "normal")
    assert all(type(r[k]) is str for k in ("recording_id", "fault_type", "severity")) and type(r["window_index"]) is int
    assert any(e["matches"] == "BPFI" for e in evidence("IR021_3", 40))
    assert evidence("Normal_3", 100) == []
    w = get_window("IR021_3", 40, max_points=512)
    assert len(w["samples"]) == 512 and w["sample_rate_hz"] == 3000 and get_window("IR021_3", 40)["samples"][::4] == w["samples"]
    t = []
    for i in range(20):
        t0 = time.perf_counter()
        predict("OR021@6_3", i)
        t.append(time.perf_counter() - t0)
    print(f"interface ok; cold predict {cold * 1000:.0f} ms, warm median {sorted(t)[10] * 1000:.0f} ms, max {max(t) * 1000:.0f} ms")

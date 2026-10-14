"""Self-check for the mock API:  python -m app.api.test_api   (from the repo root; also works with pytest).

Reads docs/contract.md and checks the API output against the JSON samples in it, so the mock and the contract
cannot drift apart without a failing test.
"""
import ast
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from . import mock_data, uncertainty
from .main import ANALYSES, app

client = TestClient(app)
CONTRACT = Path(__file__).resolve().parents[2] / "docs" / "contract.md"


def _contract_samples():
    blocks = [json.loads(b) for b in re.findall(r"```json\n(.*?)```", CONTRACT.read_text(encoding="utf-8"), re.S)]
    sensor = next(b for b in blocks if "probabilities" in b)
    final = next(b for b in blocks if "request_id" in b)
    return sensor, final


def _analyze(rid="OR007@6_0", idx=12):
    r = client.post("/analyze", json={"recording_id": rid, "window_index": idx})
    assert r.status_code == 200, r.text
    return r.json()


def test_root_redirects_to_docs():
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/docs"


def test_health():
    r = client.get("/health").json()
    assert r["status"] == "ok" and r["mode"] == "mock"
    assert set(r["parts"]) == {"api", "sensor", "retrieval", "llm"}


def test_recordings():
    recs = client.get("/recordings").json()
    assert len(recs) == 40 and len({r["recording_id"] for r in recs}) == 40
    assert set(recs[0]) == {"recording_id", "load_hp", "rpm", "fault_type", "severity", "n_windows", "held_out"}
    assert sum(r["held_out"] for r in recs) == 10  # the 3 hp recordings


def test_recordings_match_sensor_package():
    """Compare with sensor/data_loading.py by reading its source (no numpy or scipy needed)."""
    tree = ast.parse((CONTRACT.parents[1] / "sensor" / "data_loading.py").read_text(encoding="utf-8"))
    consts = {t.id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
              for t in n.targets if isinstance(t, ast.Name) and t.id in ("CONDITIONS", "LOADS", "SAMPLE_RATE_HZ", "WINDOW")}
    assert consts["LOADS"] == mock_data.LOADS
    assert (consts["SAMPLE_RATE_HZ"], consts["WINDOW"]) == (mock_data.SAMPLE_RATE_HZ, mock_data.WINDOW)
    assert [(p, ft, sev) for p, ft, sev, _ in consts["CONDITIONS"]] == mock_data.CONDITIONS


def test_signal():
    r = client.get("/signal", params={"recording_id": "IR014_1", "window_index": 5}).json()
    assert len(r["samples"]) == 512 and r["sample_rate_hz"] == 12000 / 4
    full = client.get("/signal", params={"recording_id": "IR014_1", "window_index": 5, "max_points": 2048}).json()
    assert len(full["samples"]) == 2048 and full["sample_rate_hz"] == 12000
    assert client.get("/signal", params={"recording_id": "IR014_1", "window_index": 5}).json() == r  # deterministic
    assert client.get("/signal", params={"recording_id": "nope"}).status_code == 404
    assert client.get("/signal", params={"recording_id": "IR014_1", "window_index": 117}).status_code == 422


def test_analyze_matches_contract():
    sensor_sample, final_sample = _contract_samples()
    a = _analyze()
    assert {k: v for k, v in a["sensor"].items() if k != "evidence"} == sensor_sample  # exact contract sample
    assert set(a) == set(final_sample)
    assert set(a["meta"]) == set(final_sample["meta"])
    assert set(a["meta"]["latency_ms"]) == set(final_sample["meta"]["latency_ms"])
    assert set(a["uncertainty"]) == set(final_sample["uncertainty"])
    assert set(a["recommended_actions"][0]) == set(final_sample["recommended_actions"][0])
    assert set(a["citations"][0]) == set(final_sample["citations"][0])
    assert set(a["sensor"]) - {"evidence"} == set(sensor_sample)  # evidence is the one optional extra


def test_every_recording_gives_a_consistent_answer():
    levels = set()
    for rec in client.get("/recordings").json():
        for idx in range(0, 117, 13):
            a = _analyze(rec["recording_id"], idx)
            s = a["sensor"]
            assert s["fault_type"] == rec["fault_type"] and s["severity"] == rec["severity"]
            assert abs(sum(s["probabilities"].values()) - 1.0) < 0.011 or (s["recording_id"], idx) == mock_data.GOLDEN
            assert s["probabilities"][s["fault_type"]] == s["confidence"]
            assert a["uncertainty"]["level"] == uncertainty.level(s["confidence"])
            levels.add(a["uncertainty"]["level"])
            ids = {c["id"] for c in a["citations"]}
            assert all(set(act["citation_ids"]) <= ids for act in a["recommended_actions"])  # citations only from retrieved
            assert a["explanation"].startswith("[MOCK]") and a["meta"]["model"] == "mock"
            assert a["needs_human_confirm"] == (a["uncertainty"]["level"] == "high" or any(x["safety_critical"] for x in a["recommended_actions"]))
            if s["fault_type"] == "normal":
                assert s["evidence"] == [] and not any(x["safety_critical"] for x in a["recommended_actions"])
            if a["uncertainty"]["level"] == "high":
                assert "not sure" in a["explanation"] and "manual inspection" in a["recommended_actions"][0]["step"]
    assert levels == {"low", "medium", "high"}  # the screen can show every state


def test_analyze_is_deterministic_and_ids_increase():
    a, b = _analyze("B014_2", 40), _analyze("B014_2", 40)
    assert {k: v for k, v in a.items() if k != "request_id"} == {k: v for k, v in b.items() if k != "request_id"}
    assert a["request_id"] != b["request_id"] and re.fullmatch(r"req-\d{4}", a["request_id"])


def test_analyze_errors():
    assert client.post("/analyze", json={"recording_id": "nope", "window_index": 0}).status_code == 404
    assert client.post("/analyze", json={"recording_id": "B014_2", "window_index": 999}).status_code == 422
    assert client.post("/analyze", json={"recording_id": "B014_2", "window_index": -1}).status_code == 422
    assert client.post("/analyze", json={"recording_id": "B014_2"}).status_code == 422


def test_confirm():
    rid = _analyze()["request_id"]
    r = client.post("/confirm", json={"request_id": rid, "decision": "confirmed"})
    assert r.status_code == 200 and r.json()["decision"] == "confirmed" and rid in ANALYSES
    assert client.post("/confirm", json={"request_id": rid, "decision": "escalated"}).json()["decision"] == "escalated"
    assert client.post("/confirm", json={"request_id": "req-9999", "decision": "confirmed"}).status_code == 404
    assert client.post("/confirm", json={"request_id": rid, "decision": "maybe"}).status_code == 422


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print("ok  ", name)
    print(f"{len(tests)} checks passed")

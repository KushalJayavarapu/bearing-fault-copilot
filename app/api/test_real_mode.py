"""Self-check for MOCK_MODE=false (real sensor + real retrieval wiring), with fakes in their place so it needs no
CWRU data, models, retrieval index or key:  python -m app.api.test_real_mode

What the real parts do is tested by their owners (sensor/test_sensor.py, rag/test_suite.py). This checks that the API
connects them correctly: request shapes, error handling, health, warm-up and that nothing breaks in mock mode."""
import json
import logging
import sys
from contextlib import contextmanager
from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

from . import main, mock_data
from .llm import LLMClient
from .schemas import FinalAnswer
from .test_orchestrator import GOOD

logging.getLogger("app.api").addHandler(logging.NullHandler())
logging.getLogger("app.orchestrator").addHandler(logging.NullHandler())

RECS = [{"recording_id": "OR007@6_3", "load_hp": 3, "rpm": 1730, "fault_type": "outer_race", "severity": "small",
         "n_windows": 20, "held_out": True},
        {"recording_id": "Normal_3", "load_hp": 3, "rpm": 1730, "fault_type": "normal", "severity": "none",
         "n_windows": 20, "held_out": True}]
RAG_PASSAGES = [{"chunk_id": "bridge-outer-p3", "text": "Stop the machine and isolate the power before opening the housing.",
                 "source_title": "Bridge table", "source_type": "playbook", "page": 3, "url": "data/knowledge/bridge_table.md"}]
LLM_REPLY = json.dumps({
    "explanation": "A strong outer race peak matches the classifier. A manual check should confirm it.",
    "likely_causes": ["Fatigue"],
    "recommended_actions": [{"step": "Stop the machine and isolate the power.", "safety_critical": True,
                             "citation_ids": ["bridge-outer-p3", "invented-id"]}]})


class FakeSensor:
    """Same four functions as sensor/predict.py."""
    def __init__(self, fail=False):
        self.fail, self.calls = fail, []

    def list_recordings(self):
        return [dict(r) for r in RECS]

    def predict(self, recording_id, window_index):
        self.calls.append(("predict", recording_id, window_index))
        if self.fail:
            raise RuntimeError("model file missing")
        return {**mock_data.sensor_result("OR007@6_3", 2), "recording_id": recording_id, "window_index": window_index}

    def get_window(self, recording_id, window_index, max_points=None):
        self.calls.append(("get_window", recording_id, window_index, max_points))
        return {"samples": [0.0, 0.5, -0.5][: max_points or 3], "sample_rate_hz": 12000}


@contextmanager
def real_mode(sensor=None, retrieve=None, llm=True, llm_mock=False):
    """Switch main to MOCK_MODE=false with fakes, and put everything back afterwards."""
    keep = {k: getattr(main, k) for k in ("MOCK_MODE", "LLM_MOCK", "_llm", "_sensor_mod", "_rag_retrieve", "_table")}
    status = dict(main._status)
    rag_calls, llm_bodies = [], []

    def default_rag(request):
        rag_calls.append(request)
        return {"passages": RAG_PASSAGES}

    def handler(req):
        llm_bodies.append(json.loads(req.read()))
        return httpx.Response(200, json={"model": "gateway-name", "choices": [{"message": {"content": LLM_REPLY}}]})
    try:
        main.MOCK_MODE, main.LLM_MOCK, main._table = False, llm_mock, None
        main._sensor_mod = sensor or FakeSensor()
        main._rag_retrieve = retrieve or default_rag
        main._llm = LLMClient("http://llm.test/v1", "k", "my-model", transport=httpx.MockTransport(handler),
                              sleep=lambda s: None) if llm else None
        main._status.update(sensor="not checked", retrieval="not checked")
        yield SimpleNamespace(client=TestClient(main.app), sensor=main._sensor_mod, rag_calls=rag_calls, llm=llm_bodies)
    finally:
        for k, v in keep.items():
            setattr(main, k, v)
        main._status.update(status)


BODY = {"recording_id": "OR007@6_3", "window_index": 2}


def test_real_recordings_and_signal_come_from_the_sensor_package():
    with real_mode() as m:
        recs = m.client.get("/recordings").json()
        assert [r["recording_id"] for r in recs] == ["OR007@6_3", "Normal_3"]  # only what the sensor says has data
        s = m.client.get("/signal", params={"recording_id": "OR007@6_3", "window_index": 4, "max_points": 16}).json()
        assert s == {"samples": [0.0, 0.5, -0.5], "sample_rate_hz": 12000}
        assert ("get_window", "OR007@6_3", 4, 16) in m.sensor.calls
        assert m.client.get("/signal", params={"recording_id": "IR014_1"}).status_code == 404  # no data in this build
        assert m.client.get("/signal", params={"recording_id": "OR007@6_3", "window_index": 20}).status_code == 422


def test_real_analyze_connects_sensor_retrieval_and_llm():
    with real_mode() as m:
        r = m.client.post("/analyze", json=BODY)
        assert r.status_code == 200, r.text
        a = r.json()
        FinalAnswer(**a)
        assert m.sensor.calls == [("predict", "OR007@6_3", 2)]
        assert m.rag_calls == [{"query": "outer race defect, small, deep groove ball bearing: causes and actions",
                                "fault_type": "outer_race", "severity": "small", "top_k": 5}]  # contract section 2
        assert [c["id"] for c in a["citations"]] == ["bridge-outer-p3"]  # from the real retrieval, invented id dropped
        assert a["citations"][0]["source_title"] == "Bridge table" and a["meta"]["model"] == "my-model"
        assert a["recommended_actions"][0]["safety_critical"] is True and a["needs_human_confirm"] is True
        lat = a["meta"]["latency_ms"]
        assert 0 <= lat["classifier"] < 1000 and lat["classifier"] != 88  # measured, not the mock's fixed 88
        assert "vibration_evidence" in m.llm[0]["messages"][1]["content"] and "bridge-outer-p3" in m.llm[0]["messages"][1]["content"]
        assert m.client.post("/confirm", json={"request_id": a["request_id"], "decision": "confirmed"}).status_code == 200


def test_real_mode_health_shows_what_is_real():
    with real_mode() as m:
        assert m.client.get("/health").json() == {"status": "ok", "mode": "real", "parts": {
            "api": "ok", "sensor": "real", "retrieval": "real", "llm": "live"}}
    with real_mode(llm_mock=True) as m:
        h = m.client.get("/health").json()
        assert h["mode"] == "mixed" and h["parts"]["llm"] == "mock" and h["parts"]["sensor"] == "real"


def test_real_sensor_with_canned_text_when_llm_is_mocked():
    with real_mode(llm=False, llm_mock=True) as m:  # no LLM configured at all: not needed
        a = m.client.post("/analyze", json=BODY).json()
        assert a["explanation"].startswith("[MOCK]") and a["sensor"]["recording_id"] == "OR007@6_3"
        assert m.sensor.calls == [("predict", "OR007@6_3", 2)] and m.rag_calls == []


def test_real_mode_errors_are_clear_not_crashes():
    with real_mode(sensor=FakeSensor(fail=True)) as m:
        r = m.client.post("/analyze", json=BODY)
        assert r.status_code == 500 and "classifier failed" in r.json()["detail"] and "model file missing" in r.json()["detail"]
    with real_mode(llm=False) as m:  # real LLM wanted, nothing configured
        import os
        saved = {k: os.environ.pop(k, None) for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")}
        try:
            r = m.client.post("/analyze", json=BODY)
        finally:
            os.environ.update({k: v for k, v in saved.items() if v is not None})
        assert r.status_code == 503 and "LLM_API_KEY" in r.json()["detail"] and m.sensor.calls == []  # fails before work
    with real_mode() as m:
        assert m.client.post("/analyze", json={"recording_id": "IR014_1", "window_index": 0}).status_code == 404


def test_retrieval_down_gives_a_degraded_answer_not_a_crash():
    def broken(request):
        raise RuntimeError("index not built")
    with real_mode(retrieve=broken) as m:
        r = m.client.post("/analyze", json=BODY)
        assert r.status_code == 200 and r.json()["explanation"].startswith("No supporting reference passages")
        assert r.json()["sensor"]["fault_type"] == "outer_race" and m.llm == []  # LLM not called without passages


def test_missing_sensor_package_is_a_clear_503():
    saved = sys.modules.get("sensor.predict", "absent")
    with real_mode() as m:
        main._sensor_mod, main._table = None, None
        sys.modules["sensor.predict"] = None  # makes "from sensor import predict" fail like a missing dependency
        try:
            r = m.client.get("/recordings")
        finally:
            if saved == "absent":
                sys.modules.pop("sensor.predict", None)
            else:
                sys.modules["sensor.predict"] = saved
        assert r.status_code == 503 and "sensor package could not be loaded" in r.json()["detail"]


def test_no_recordings_found_is_a_clear_503():
    class Empty(FakeSensor):
        def list_recordings(self):
            return []
    with real_mode(sensor=Empty()) as m:
        r = m.client.get("/recordings")
        assert r.status_code == 503 and "python -m sensor.build" in r.json()["detail"]


def test_warm_up_loads_everything_and_reports_problems_in_health():
    with real_mode() as m:
        main._warm_up()
        assert main._status == {"sensor": "ok", "retrieval": "ok"} and m.sensor.calls == [("predict", "OR007@6_3", 0)]
        assert m.rag_calls[0]["top_k"] == 1 and m.client.get("/health").json()["status"] == "ok"

    def broken(request):
        raise FileNotFoundError("rag/index missing: run python -m rag.build")
    with real_mode(sensor=FakeSensor(fail=True), retrieve=broken) as m:
        main._warm_up()  # must not raise: the server still starts and says what is wrong
        h = m.client.get("/health").json()
        assert h["status"] == "degraded" and h["parts"]["sensor"] == "error: RuntimeError: model file missing"
        assert h["parts"]["retrieval"].startswith("error: FileNotFoundError") and h["parts"]["api"] == "ok"


def test_mock_mode_never_imports_the_real_parts():
    """With the real packages made un-importable, every endpoint must still work in mock mode."""
    assert main.MOCK_MODE is True  # the default, untouched by the tests above
    keep = main._sensor_mod, main._rag_retrieve, main.LLM_MOCK, main._llm
    saved = {k: sys.modules.get(k, "absent") for k in ("sensor.predict", "rag.retrieve")}
    sys.modules["sensor.predict"] = sys.modules["rag.retrieve"] = None
    main._sensor_mod = main._rag_retrieve = None
    try:
        c = TestClient(main.app)
        assert len(c.get("/recordings").json()) == 40
        assert c.get("/signal", params={"recording_id": "IR014_1"}).status_code == 200
        assert c.post("/analyze", json=BODY).json()["explanation"].startswith("[MOCK]")
        main.LLM_MOCK, main._llm = False, LLMClient("http://llm.test/v1", "k", "m", sleep=lambda s: None, transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={"choices": [{"message": {"content": GOOD}}]})))
        live = c.post("/analyze", json=BODY).json()  # real LLM on mock data: uses the stub retrieval, not rag.retrieve
        assert live["citations"][0]["id"].startswith("stub-") and live["meta"]["model"] == "m"
        assert c.get("/health").json()["parts"]["sensor"] == "mock"
        assert main._sensor_mod is None and main._rag_retrieve is None
    finally:
        main._sensor_mod, main._rag_retrieve, main.LLM_MOCK, main._llm = keep
        for k, v in saved.items():
            if v == "absent":
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print("ok  ", name)
    print(f"{len(tests)} checks passed")

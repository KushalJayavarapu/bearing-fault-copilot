"""Backend API (contract: docs/contract.md). Run:  python -m app   then open http://localhost:8080/docs

Two switches, both read from the environment (.env):
- MOCK_MODE (default true): true = canned sensor data and stub retrieval, so the screen, the tests and the video need
  no models, data or key. false = the real classifier (sensor/predict.py) and the real retrieval (rag/retrieve.py);
  they are imported only then, and need `python -m sensor.build` and `python -m rag.build` to have been run.
- LLM_MOCK (default = MOCK_MODE): true = canned explanation, false = the real LLM (LLM_BASE_URL, LLM_API_KEY,
  LLM_MODEL). MOCK_MODE=true with LLM_MOCK=false shows real text on mock data; MOCK_MODE=false with LLM_MOCK=true
  shows the real classifier with canned text (handy when the LLM is rate limited).
GET /health shows what is mock, what is real, and, for a real part that failed to load, why.
"""
import itertools
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool

from . import mock_data as mock
from . import orchestrator, retrieval_stub
from .llm import LLMClient, LLMError
from .schemas import (AnalyzeRequest, Confirmation, ConfirmRequest, FinalAnswer, Health, Recording, Signal)

log = logging.getLogger("app.api")
MOCK_MODE = os.environ.get("MOCK_MODE", "true").lower() == "true"
LLM_MOCK = os.environ.get("LLM_MOCK", str(MOCK_MODE)).lower() == "true"  # canned explanation instead of the LLM

_lock = threading.Lock()
_ids = itertools.count(1)
ANALYSES: dict[str, dict] = {}  # request_id -> answer, so /confirm can check the id exists
CONFIRMATIONS: dict[str, dict] = {}
_llm: LLMClient | None = None
_sensor_mod = None  # sensor.predict, imported on first use in real mode
_rag_retrieve = None  # rag.retrieve.retrieve, imported on first use in real mode
_table: dict[str, dict] | None = None  # real recordings that have data, by id
_status = {"sensor": "not checked", "retrieval": "not checked"}  # "ok" or an error text, set by _warm_up()


def _why(e):
    return e.detail if isinstance(e, HTTPException) else f"{type(e).__name__}: {e}"


def _get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        try:
            _llm = LLMClient.from_env()
        except LLMError as e:
            raise HTTPException(503, str(e))
    return _llm


def _sensor():
    global _sensor_mod
    if _sensor_mod is None:
        try:
            from sensor import predict as module  # imports numpy and scikit-learn: only needed in real mode
        except Exception as e:
            raise HTTPException(503, f"The sensor package could not be loaded ({type(e).__name__}: {e}). "
                                     "Install sensor/requirements.txt, or set MOCK_MODE=true.")
        _sensor_mod = module
    return _sensor_mod


def _retrieve(request):
    global _rag_retrieve
    if _rag_retrieve is None:
        from rag.retrieve import retrieve  # an import error is caught by the orchestrator: degraded answer + log line
        _rag_retrieve = retrieve
    return _rag_retrieve(request)


def _recording_table() -> dict[str, dict]:
    """recording_id -> metadata. Real mode: only recordings whose data file is present (cached once found)."""
    global _table
    if MOCK_MODE:
        return {r["recording_id"]: r for r in mock.list_recordings()}
    if _table is None:
        try:
            found = {r["recording_id"]: r for r in _sensor().list_recordings()}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(503, f"The recordings could not be listed ({_why(e)}). Run python -m sensor.build.")
        if not found:
            raise HTTPException(503, "No CWRU recordings found. Run python -m sensor.build (or set SENSOR_DATA_DIR).")
        _table = found
    return _table


def _check(recording_id: str, window_index: int):
    rec = _recording_table().get(recording_id)
    if rec is None:
        raise HTTPException(404, f"Unknown recording_id '{recording_id}'. See GET /recordings.")
    if window_index >= rec["n_windows"]:
        raise HTTPException(422, f"window_index must be between 0 and {rec['n_windows'] - 1}.")


def _sensor_result(recording_id, window_index):
    """(sensor result in the contract shape, classifier milliseconds)."""
    if MOCK_MODE:
        return mock.sensor_result(recording_id, window_index), 88
    t = time.perf_counter()
    try:
        result = _sensor().predict(recording_id, window_index)
    except HTTPException:
        raise
    except Exception as e:
        log.exception("classifier failed for %s window %s", recording_id, window_index)
        raise HTTPException(500, f"The classifier failed ({_why(e)}).")
    return result, round((time.perf_counter() - t) * 1000)


def _warm_up():
    """Real mode: load the classifier and the retrieval index once at startup, so the first request is not slow and
    a broken install shows up in the log and in GET /health instead of in the middle of a demo."""
    if MOCK_MODE:
        return
    t = time.perf_counter()
    try:
        _sensor().predict(next(iter(_recording_table())), 0)
        _status["sensor"] = "ok"
    except Exception as e:
        _status["sensor"] = f"error: {_why(e)}"
        log.error("classifier is not ready: %s", _status["sensor"])
    try:
        _retrieve({"query": "bearing warm-up", "fault_type": "normal", "severity": "none", "top_k": 1})
        _status["retrieval"] = "ok"
    except Exception as e:
        _status["retrieval"] = f"error: {_why(e)}"
        log.error("retrieval is not ready: %s", _status["retrieval"])
    log.info("warm-up done in %d ms: sensor=%s retrieval=%s", (time.perf_counter() - t) * 1000,
             _status["sensor"], _status["retrieval"])


@asynccontextmanager
async def lifespan(_app):
    await run_in_threadpool(_warm_up)
    yield


app = FastAPI(title="Bearing fault copilot API", version="0.2", lifespan=lifespan,
              description="Detect, explain, act. Data shapes follow docs/contract.md.")
app.add_middleware(CORSMiddleware, allow_methods=["*"], allow_headers=["*"],
                   allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")])


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/health", response_model=Health)
def health():
    def part(name):
        if MOCK_MODE:
            return "mock"
        return "real" if _status[name] in ("ok", "not checked") else _status[name]
    parts = {"api": "ok", "sensor": part("sensor"), "retrieval": part("retrieval"), "llm": "mock" if LLM_MOCK else "live"}
    overall = "mock" if MOCK_MODE and LLM_MOCK else "real" if not MOCK_MODE and not LLM_MOCK else "mixed"
    return {"status": "degraded" if any(v.startswith("error") for v in parts.values()) else "ok",
            "mode": overall, "parts": parts}


@app.get("/recordings", response_model=list[Recording])
def recordings():
    return list(_recording_table().values())


@app.get("/signal", response_model=Signal)
def signal(recording_id: str, window_index: int = Query(0, ge=0), max_points: int = Query(512, ge=16, le=2048)):
    _check(recording_id, window_index)
    if MOCK_MODE:
        return mock.window(recording_id, window_index, max_points)
    return _sensor().get_window(recording_id, window_index, max_points)


@app.post("/analyze", response_model=FinalAnswer, response_model_exclude_none=True)
def analyze(body: AnalyzeRequest):
    _check(body.recording_id, body.window_index)
    llm = None if LLM_MOCK else _get_llm()  # a missing key is a clear 503 before any work is done
    sensor, classifier_ms = _sensor_result(body.recording_id, body.window_index)
    with _lock:
        request_id = f"req-{next(_ids):04d}"
    if llm is None:
        answer = {**mock.answer_for(sensor), "request_id": request_id}
    else:
        answer = orchestrator.analyze(sensor, retrieve=retrieval_stub.retrieve if MOCK_MODE else _retrieve, llm=llm,
                                      request_id=request_id, classifier_ms=classifier_ms,
                                      served_on=os.environ.get("LLM_SERVED_ON", "unknown"))
    ANALYSES[request_id] = answer
    return answer


@app.post("/confirm", response_model=Confirmation)
def confirm(body: ConfirmRequest):
    if body.request_id not in ANALYSES:
        raise HTTPException(404, f"Unknown request_id '{body.request_id}'. Call POST /analyze first.")
    record = {"request_id": body.request_id, "decision": body.decision,
              "confirmed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    CONFIRMATIONS[body.request_id] = record
    return record

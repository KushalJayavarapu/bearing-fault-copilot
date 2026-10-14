"""Backend API (contract: docs/contract.md). Run:  python -m app   then open http://localhost:8080/docs

MOCK_MODE=true (the default until the real parts are wired in) serves canned data in the contract shape,
so the screen, the tests and the video can be built without models, data or an LLM key.
With MOCK_MODE=false the data endpoints answer 501 until the real pipeline is connected.
With MOCK_MODE=true and LLM_MOCK=false the sensor and retrieval stay mock/stub but the explanation comes from the
real LLM (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL): that is how the screen shows real text before everything is wired.
"""
import itertools
import os
import threading
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from . import mock_data as mock
from . import orchestrator, retrieval_stub
from .llm import LLMClient, LLMError
from .schemas import (AnalyzeRequest, Confirmation, ConfirmRequest, FinalAnswer, Health, Recording, Signal)

MOCK_MODE = os.environ.get("MOCK_MODE", "true").lower() == "true"
LLM_MOCK = os.environ.get("LLM_MOCK", str(MOCK_MODE)).lower() == "true"  # canned explanation instead of the LLM

app = FastAPI(title="Bearing fault copilot API", version="0.1-mock",
              description="Detect, explain, act. Data shapes follow docs/contract.md.")
app.add_middleware(CORSMiddleware, allow_methods=["*"], allow_headers=["*"],
                   allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")])

_lock = threading.Lock()
_ids = itertools.count(1)
ANALYSES: dict[str, dict] = {}  # request_id -> answer, so /confirm can check the id exists
CONFIRMATIONS: dict[str, dict] = {}
_llm: LLMClient | None = None


def _get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        try:
            _llm = LLMClient.from_env()
        except LLMError as e:
            raise HTTPException(503, str(e))
    return _llm


def _need_mock():
    if not MOCK_MODE:
        raise HTTPException(501, "The real pipeline is not connected yet. Set MOCK_MODE=true.")


def _check(recording_id: str, window_index: int):
    _need_mock()
    if recording_id not in mock.RECORDINGS:
        raise HTTPException(404, f"Unknown recording_id '{recording_id}'. See GET /recordings.")
    if window_index >= mock.N_WINDOWS:
        raise HTTPException(422, f"window_index must be between 0 and {mock.N_WINDOWS - 1}.")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/health", response_model=Health)
def health():
    mode = "mock" if MOCK_MODE else "real"
    llm = "mock" if LLM_MOCK else "live"
    overall = "mock" if MOCK_MODE and LLM_MOCK else "mixed" if MOCK_MODE else "real"
    return {"status": "ok", "mode": overall, "parts": {"api": "ok", "sensor": mode, "retrieval": mode, "llm": llm}}


@app.get("/recordings", response_model=list[Recording])
def recordings():
    _need_mock()
    return mock.list_recordings()


@app.get("/signal", response_model=Signal)
def signal(recording_id: str, window_index: int = Query(0, ge=0), max_points: int = Query(512, ge=16, le=2048)):
    _check(recording_id, window_index)
    return mock.window(recording_id, window_index, max_points)


@app.post("/analyze", response_model=FinalAnswer, response_model_exclude_none=True)
def analyze(body: AnalyzeRequest):
    _check(body.recording_id, body.window_index)
    with _lock:
        request_id = f"req-{next(_ids):04d}"
    if LLM_MOCK:
        answer = {**mock.analyze(body.recording_id, body.window_index), "request_id": request_id}
    else:
        answer = orchestrator.analyze(mock.sensor_result(body.recording_id, body.window_index),
                                      retrieve=retrieval_stub.retrieve, llm=_get_llm(), request_id=request_id,
                                      classifier_ms=88, served_on=os.environ.get("LLM_SERVED_ON", "unknown"))
    ANALYSES[request_id] = answer
    return answer


@app.post("/confirm", response_model=Confirmation)
def confirm(body: ConfirmRequest):
    _need_mock()
    if body.request_id not in ANALYSES:
        raise HTTPException(404, f"Unknown request_id '{body.request_id}'. Call POST /analyze first.")
    record = {"request_id": body.request_id, "decision": body.decision,
              "confirmed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    CONFIRMATIONS[body.request_id] = record
    return record

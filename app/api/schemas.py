"""Request and response shapes. They mirror docs/contract.md, so /docs shows exactly what the contract says.

Optional fields are left out of the JSON when empty (response_model_exclude_none), so a result without
`evidence` looks exactly like contract section 1.
"""
from typing import Literal

from pydantic import BaseModel, Field

FaultType = Literal["normal", "inner_race", "outer_race", "ball"]
Severity = Literal["none", "small", "medium", "large"]
Level = Literal["low", "medium", "high"]
Decision = Literal["confirmed", "escalated"]


class Context(BaseModel):
    sensor: str
    sample_rate_hz: int
    load_hp: int
    rpm: int


class Evidence(BaseModel):
    """Optional physics fact behind a sensor call (Harshit's proposal, not frozen in the contract yet)."""
    feature: str
    freq_hz: float | None = None
    expected_hz: float | None = None
    value: float | None = None
    matches: str
    harmonic: int | None = None
    vs_normal: float
    strength: Literal["low", "medium", "high"]


class SensorResult(BaseModel):
    recording_id: str
    window_index: int
    fault_type: FaultType
    severity: Severity
    confidence: float
    probabilities: dict[FaultType, float]
    context: Context
    evidence: list[Evidence] | None = None


class Action(BaseModel):
    step: str
    safety_critical: bool
    citation_ids: list[str]


class Citation(BaseModel):
    id: str
    source_title: str
    page: int | None = None
    url: str
    excerpt: str


class Uncertainty(BaseModel):
    level: Level
    note: str


class LatencyMs(BaseModel):
    classifier: int
    retrieval: int
    llm: int
    total: int


class Meta(BaseModel):
    model: str
    served_on: str
    latency_ms: LatencyMs


class FinalAnswer(BaseModel):
    request_id: str
    sensor: SensorResult
    explanation: str
    likely_causes: list[str]
    recommended_actions: list[Action]
    needs_human_confirm: bool
    citations: list[Citation]
    uncertainty: Uncertainty
    meta: Meta


class AnalyzeRequest(BaseModel):
    recording_id: str
    window_index: int = Field(ge=0)


class ConfirmRequest(BaseModel):
    request_id: str
    decision: Decision


class Confirmation(BaseModel):
    request_id: str
    decision: Decision
    confirmed_at: str


class Recording(BaseModel):
    recording_id: str
    load_hp: int
    rpm: int
    fault_type: FaultType
    severity: Severity
    n_windows: int
    held_out: bool


class Signal(BaseModel):
    samples: list[float]
    sample_rate_hz: float


class Health(BaseModel):
    status: str
    mode: str
    parts: dict[str, str]

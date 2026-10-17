from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import requests
import streamlit as st
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")
MOCK = os.getenv("MOCK", "true").strip().lower() in {"1", "true", "yes", "on"}
API_URL = os.getenv("API_URL", "http://localhost:8080").rstrip("/")
# real mode: show only recordings the demo model never trained on (3 hp), unless ALL_RECORDINGS=true
ALL_RECORDINGS = os.getenv("ALL_RECORDINGS", "false").strip().lower() in {"1", "true", "yes", "on"}
MOCK_DATA = json.loads((BASE / "mock_data" / "sample.json").read_text(encoding="utf-8"))

FAULTS = {
    "normal": {"name": "Healthy", "short": "NORMAL", "color": "#31c48d", "icon": "✓", "description": "No fault indicated in this assessment."},
    "inner_race": {"name": "Inner-race fault", "short": "INNER RACE", "color": "#ff6b6b", "icon": "!", "description": "Potential damage on the bearing's inner ring."},
    "outer_race": {"name": "Outer-race fault", "short": "OUTER RACE", "color": "#ff6b6b", "icon": "!", "description": "Potential damage on the bearing's outer ring."},
    "ball": {"name": "Rolling-ball fault", "short": "BALL FAULT", "color": "#ff6b6b", "icon": "!", "description": "Potential damage to a rolling element."},
}
SEVERITY_COLORS = {"none": "#31c48d", "small": "#f6c453", "medium": "#ff9f43", "large": "#ff6b6b"}

st.set_page_config(page_title="BearingGuard | Industrial Intelligence", page_icon="⚙️", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --bg:#090e17; --panel:#111a28; --panel2:#0d1521; --line:#263548; --text:#edf3fb; --muted:#91a2b8; --cyan:#69dcff; --green:#31c48d; }
html, body, [class*="css"] { font-family:'Manrope',sans-serif; }
.stApp { background:radial-gradient(ellipse at 10% 0%,#14283b 0%,#090e17 43%,#090e17 100%); color:var(--text); }
.block-container { max-width:1500px; padding-top:1.4rem; padding-bottom:2.5rem; }
[data-testid="stHeader"] { background:transparent; }
section[data-testid="stMain"] { color:var(--text); }
#MainMenu, footer { visibility:hidden; }
.brand { display:flex; align-items:center; gap:13px; }
.brand-icon { width:48px;height:48px;border-radius:14px;display:flex;align-items:center;justify-content:center;background:linear-gradient(145deg,#18394b,#10202e);border:1px solid #2b5367;color:#72e0ff;font-size:25px;box-shadow:0 0 30px #35bce51a; }
.brand-name { font-weight:800;font-size:25px;letter-spacing:-.8px;color:#f2f7ff;line-height:1.15; }
.brand-sub { color:#91a2b8;font-size:11px;letter-spacing:2px;text-transform:uppercase;margin-top:5px; }
.top-pill { border:1px solid #2b4655;background:#10212c;color:#8ee8ff;border-radius:999px;padding:8px 12px;font-size:11px;font-weight:800;letter-spacing:1px;display:inline-block; }
.status-line { color:#8fa2b8;font-size:12px; }
.section-label { font-size:11px;letter-spacing:1.7px;text-transform:uppercase;color:#91a7bf;font-weight:800;margin:4px 0 12px; }
.panel { background:linear-gradient(145deg,#121d2c,#0e1724);border:1px solid #27374a;border-radius:17px;padding:19px 20px;margin-bottom:14px;box-shadow:0 12px 34px #00000014; }
.panel-title { font-size:16px;font-weight:800;color:#edf4fc;margin-bottom:5px; }
.panel-sub { font-size:12px;color:#8ea1b8; }
.metric-card { background:#101a27;border:1px solid #263649;border-radius:13px;padding:15px 16px;min-height:91px; }
.metric-label { color:#90a3b9;font-size:10px;letter-spacing:1.4px;text-transform:uppercase;font-weight:800; }
.metric-value { color:#f1f6ff;font-size:21px;font-weight:800;margin-top:8px;letter-spacing:-.4px; }
.metric-note { color:#8da0b7;font-size:11px;margin-top:3px; }
.fault-banner { border-radius:16px;padding:20px 22px;border:1px solid #ff6b6b55;background:linear-gradient(110deg,#3b1b27,#191724 75%); }
.fault-banner.normal { border-color:#31c48d55;background:linear-gradient(110deg,#10332e,#111b27 75%); }
.fault-kicker {font-size:10px;letter-spacing:1.8px;font-weight:800;color:#ff9b9b;text-transform:uppercase;}
.fault-banner.normal .fault-kicker {color:#70e0b7;}
.fault-name {font-size:27px;font-weight:800;letter-spacing:-.8px;margin:5px 0 4px;color:#fff;}
.fault-desc {font-size:13px;color:#b6c3d4;}
.chip {display:inline-block;border:1px solid #31465a;background:#172536;color:#c3d7e8;border-radius:7px;padding:5px 8px;font-size:10px;font-weight:700;margin:3px 4px 0 0;}
.chip-red {border-color:#713f4a;background:#351e29;color:#ffb1b1;}
.chip-green {border-color:#28634f;background:#12352e;color:#8af0c8;}
.action-card {background:#101a27;border:1px solid #29394d;border-radius:12px;padding:14px 15px;margin:8px 0;}
.action-title {color:#eaf2fc;font-size:13px;font-weight:700;line-height:1.5;}
.action-meta {color:#8da0b7;font-size:11px;margin-top:7px;}
.source-box {border:1px solid #29394d;background:#0c1420;border-radius:10px;padding:12px;margin:8px 0;color:#c3d0df;font-size:12px;}
.warning {border:1px solid #9b7434;background:#322919;border-radius:10px;padding:12px 14px;color:#ffe0a1;font-size:12px;margin:10px 0;}
.safety {display:inline-block;color:#ffaaaa;background:#3c202a;border:1px solid #81414c;border-radius:5px;padding:3px 6px;font-size:9px;letter-spacing:1px;font-weight:800;}
.footnote {border-top:1px solid #243346;padding-top:15px;color:#8294aa;font-size:11px;line-height:1.7;}
div.stButton > button {border-radius:10px;min-height:42px;font-weight:800;border:1px solid #34475b;transition:all .15s ease;}
div.stButton > button[kind="primary"] {background:linear-gradient(90deg,#32bde8,#69dcff);color:#07111b;border:0;}
div.stButton > button:hover {border-color:#69dcff;color:#69dcff;}
.stSelectbox label,.stSlider label {color:#c2d0e0!important;font-weight:700!important;}
[data-testid="stMetric"] {background:#101a27;border:1px solid #263649;border-radius:12px;padding:13px 15px;}
[data-testid="stMetricLabel"] {color:#90a3b9;}
[data-testid="stMetricValue"] {color:#edf4fc;}
[data-testid="stProgressBar"] > div > div {background:linear-gradient(90deg,#31c48d,#69dcff);}
hr {border-color:#263548;}
@media(max-width:800px){.brand-name{font-size:21px}.fault-name{font-size:23px}.block-container{padding-left:1rem;padding-right:1rem}}
</style>
""", unsafe_allow_html=True)


def get_json(path: str, params: dict | None = None) -> dict:
    response = requests.get(f"{API_URL}{path}", params=params, timeout=25)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, (dict, list)):
        raise ValueError(f"{path} returned an unexpected response")
    return payload


def post_json(path: str, payload: dict) -> dict:
    response = requests.post(f"{API_URL}{path}", json=payload, timeout=90)
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError(f"{path} returned an unexpected response")
    return result


def recordings() -> list[dict]:
    if MOCK:
        rows = MOCK_DATA.get("recordings")
    else:
        rows = get_json("/recordings")
        if isinstance(rows, dict):  # older shape: {"recordings": [...]}
            rows = rows.get("recordings")
    if not isinstance(rows, list):
        raise ValueError("The recordings response is missing its recordings list")
    out = []
    for row in rows:
        if isinstance(row, dict) and row.get("recording_id"):
            row = dict(row)
            # the API calls these rpm / fault_type / n_windows; the mock sample uses older names
            row.setdefault("approx_rpm", row.get("rpm"))
            row.setdefault("true_fault_type", row.get("fault_type"))
            row.setdefault("num_windows", row.get("n_windows"))
            out.append(row)
    if not MOCK and not ALL_RECORDINGS:
        out = [r for r in out if r.get("held_out")] or out  # never present training data as a result
    return out


def true_fault(rec_id: str) -> str:
    return next((r.get("true_fault_type", "normal") for r in MOCK_DATA.get("recordings", []) if r.get("recording_id") == rec_id), "normal")


def signal(rec_id: str, index: int = 12) -> dict:
    if not MOCK:
        payload = get_json("/signal", {"recording_id": rec_id, "window_index": index})
        if not isinstance(payload, dict) or not isinstance(payload.get("samples"), list):
            raise ValueError("The signal response is missing samples")
        return payload
    # Synthetic UI-only waveform. This is not real CWRU data or a model output.
    fault = true_fault(rec_id)
    amplitudes = {"normal": 0.12, "inner_race": 0.65, "outer_race": 0.82, "ball": 0.5}
    amp = amplitudes.get(fault, 0.3)
    samples = [round(0.12 * math.sin(i * 0.075) + amp * (math.sin(i * 0.39) ** 12) * math.sin(i * 1.12), 5) for i in range(2000)]
    return {"recording_id": rec_id, "window_index": index, "sample_rate_hz": 12000, "samples": samples}


def analyze(rec_id: str, index: int = 12) -> dict:
    if not MOCK:
        return post_json("/analyze", {"recording_id": rec_id, "window_index": index})
    result = copy.deepcopy(MOCK_DATA["analysis"])
    fault = true_fault(rec_id)
    sensor = result.setdefault("sensor", {})
    sensor.update(recording_id=rec_id, window_index=index, fault_type=fault,
                  severity="none" if fault == "normal" else ("medium" if fault == "outer_race" else "small"),
                  confidence={"normal": 0.97, "inner_race": 0.91, "outer_race": 0.93, "ball": 0.88}.get(fault, 0.8))
    sensor["probabilities"] = {
        "normal": 0.97 if fault == "normal" else 0.02,
        "inner_race": 0.91 if fault == "inner_race" else 0.02,
        "outer_race": 0.93 if fault == "outer_race" else 0.02,
        "ball": 0.88 if fault == "ball" else 0.02,
    }
    result["request_id"] = f"demo-{rec_id}-{index}"
    result["explanation"] = {
        "normal": "The sample signal is shown as healthy in this interface demo. Continue routine checks and compare future readings for changes.",
        "inner_race": "The demo classifier labels this recording as a possible inner-race defect. Confirm the finding against operating conditions and a qualified inspection.",
        "outer_race": "The demo classifier labels this recording as a possible outer-race defect. Inspect the bearing and verify the result before planning maintenance.",
        "ball": "The demo classifier labels this recording as a possible rolling-element defect. Review the signal and confirm the finding with a qualified technician.",
    }.get(fault, "Demo result. Review with a qualified technician.")
    result["likely_causes"] = [] if fault == "normal" else {
        "inner_race": ["Possible fatigue or surface damage", "Lubrication or alignment issues may need inspection"],
        "outer_race": ["Possible fatigue or localized surface damage", "Contamination or mounting conditions may need inspection"],
        "ball": ["Possible rolling-element wear or surface damage", "Lubrication quality and contamination may need inspection"],
    }.get(fault, [])
    if fault == "normal":
        result["recommended_actions"] = [{"step": "Continue routine monitoring and record the next inspection reading.", "safety_critical": False, "citation_ids": ["mock-guide-p1-c1"]}]
        result["needs_human_confirm"] = False
    else:
        result["recommended_actions"] = [
            {"step": "Review the vibration trace and inspect the bearing housing using the site's approved procedure.", "safety_critical": False, "citation_ids": ["mock-guide-p1-c1"]},
            {"step": "Have a qualified technician decide whether shutdown, removal, or replacement is required.", "safety_critical": True, "citation_ids": ["mock-guide-p2-c3"]},
        ]
        result["needs_human_confirm"] = True
    result["uncertainty"] = {"level": "medium" if fault == "ball" else "low", "note": "This is simulated demo output, not a validated diagnosis."}
    result["meta"] = {"model": "mock-model", "served_on": "AMD not connected (mock)", "latency_ms": {"classifier": 12, "retrieval": 40, "llm": 1800, "total": 1900}}
    return result


def render_header() -> None:
    left, right = st.columns([3, 1.25], vertical_alignment="center")
    with left:
        st.markdown('<div class="brand"><div class="brand-icon">⚙</div><div><div class="brand-name">BearingGuard<span style="color:#69dcff">.</span></div><div class="brand-sub">Industrial intelligence · Predictive maintenance</div></div></div>', unsafe_allow_html=True)
    with right:
        if MOCK:
            st.markdown('<div style="text-align:right"><span class="top-pill">● DEMO MODE</span><div class="status-line" style="margin-top:8px">Mock data · GPU not connected</div></div>', unsafe_allow_html=True)
        else:
            try:
                health = requests.get(f"{API_URL}/health", timeout=5).json()
                parts = health.get("parts", {})
                line = " · ".join(f"{k} {v}" for k, v in parts.items() if k != "api")
                pill = "● LIVE" if health.get("status") == "ok" else "● DEGRADED"
            except (requests.RequestException, ValueError, AttributeError):
                pill, line = "● API UNREACHABLE", f"No answer from {API_URL}"
            st.markdown(f'<div style="text-align:right"><span class="top-pill">{pill}</span><div class="status-line" style="margin-top:8px">{line}</div></div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)


def render_signal_chart(sig: dict, key: str = "signal") -> None:  # key: the chart appears twice on the page
    samples = sig.get("samples") or []
    if not isinstance(samples, list) or not samples:
        st.warning("No vibration samples were returned for this recording.")
        return
    samples = samples[:2000]
    rate = sig.get("sample_rate_hz") or 12000
    x = [i / rate for i in range(len(samples))]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=samples, mode="lines", line={"color": "#69dcff", "width": 1.35}, hovertemplate="Time: %{x:.4f}s<br>Amplitude: %{y:.4f}<extra></extra>"))
    fig.update_layout(height=260, margin=dict(l=8, r=8, t=10, b=28), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(7,14,23,.35)",
                      font={"color": "#91a7bf", "size": 10}, xaxis_title="Time (seconds)", yaxis_title="Amplitude", showlegend=False,
                      xaxis={"gridcolor": "#243447", "zerolinecolor": "#34475b"}, yaxis={"gridcolor": "#243447", "zerolinecolor": "#34475b"})
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)


def render_spectrum(samples: list[float], rate: int) -> None:
    # Lightweight frequency-spectrum stretch goal; only uses the already returned chart window.
    if len(samples) < 8:
        return
    n = min(len(samples), 512)
    values = samples[:n]
    centered = [v - sum(values) / len(values) for v in values]
    magnitudes = []
    for k in range(1, min(70, n // 2)):
        real = sum(centered[t] * math.cos(2 * math.pi * k * t / n) for t in range(n))
        imag = sum(centered[t] * math.sin(2 * math.pi * k * t / n) for t in range(n))
        magnitudes.append((k * rate / n, math.sqrt(real * real + imag * imag) / n))
    fig = go.Figure(go.Scatter(x=[p[0] for p in magnitudes], y=[p[1] for p in magnitudes], mode="lines", line={"color": "#a78bfa", "width": 1.5}))
    fig.update_layout(height=190, margin=dict(l=8, r=8, t=5, b=25), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(7,14,23,.35)", font={"color": "#91a7bf", "size": 10}, xaxis_title="Frequency (Hz)", yaxis_title="Magnitude", showlegend=False, xaxis={"gridcolor": "#243447"}, yaxis={"gridcolor": "#243447"})
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="spectrum")


def render_result(data: dict, sig: dict, rec_id: str) -> None:
    sensor = data.get("sensor") if isinstance(data.get("sensor"), dict) else {}
    fault = sensor.get("fault_type", "unknown")
    fault_info = FAULTS.get(fault, {"name": "Unknown condition", "short": "UNKNOWN", "color": "#f6c453", "description": "The API returned an unrecognized fault label."})
    severity = str(sensor.get("severity", "unknown")).lower()
    confidence = sensor.get("confidence")
    confidence_ok = isinstance(confidence, (int, float)) and 0 <= confidence <= 1
    uncertainty = data.get("uncertainty") if isinstance(data.get("uncertainty"), dict) else {}
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    latency = (meta.get("latency_ms") or {}).get("total", "—")

    st.markdown('<div class="section-label">01 / Machine assessment</div>', unsafe_allow_html=True)
    normal_class = " normal" if fault == "normal" else ""
    st.markdown(f'<div class="fault-banner{normal_class}"><div class="fault-kicker">{fault_info["icon"]} &nbsp; {fault_info["short"]} DETECTED</div><div class="fault-name">{fault_info["name"]}</div><div class="fault-desc">{fault_info["description"]}</div><div style="margin-top:10px"><span class="chip">Severity: {severity.upper()}</span><span class="chip">Recording: {rec_id}</span></div></div>', unsafe_allow_html=True)
    if uncertainty.get("level") in {"medium", "high"} or (confidence_ok and confidence < 0.7):
        st.markdown(f'<div class="warning">⚠ <b>Uncertain result — technician review required.</b><br>{uncertainty.get("note", "Confidence is low; verify before taking action.")}</div>', unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("MODEL CONFIDENCE", f"{confidence:.0%}" if confidence_ok else "N/A")
    m2.metric("SEVERITY", severity.title())
    m3.metric("RESPONSE TIME", f"{latency} ms" if isinstance(latency, (int, float)) else str(latency))
    if confidence_ok:
        st.progress(float(confidence), text="Model confidence (demo value in mock mode)" if MOCK else "Model confidence")
    lat = meta.get("latency_ms") or {}
    st.caption(f"Explanation model: {meta.get('model', '—')} · Served on: {meta.get('served_on', '—')} · "
               f"classifier {lat.get('classifier', '—')} ms · retrieval {lat.get('retrieval', '—')} ms · LLM {lat.get('llm', '—')} ms")

    st.markdown('<div class="section-label" style="margin-top:22px">02 / Signal diagnostics</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><div class="panel-title">Vibration waveform</div><div class="panel-sub">Time-domain signal · Interactive hover · Up to 2,000 points</div>', unsafe_allow_html=True)
    render_signal_chart(sig, key="signal_result")
    rate = sig.get("sample_rate_hz") or 12000
    with st.expander("View frequency spectrum (experimental)"):
        st.caption("Approximate spectrum from the displayed window. This is a visualization aid, not a fault-frequency diagnosis.")
        render_spectrum(sig.get("samples") or [], rate)
    if "evidence" in sensor:
        with st.expander("Vibration evidence (physics check, independent of the classifier)"):
            for e in sensor.get("evidence") or []:
                st.write(f"**{e.get('matches', '?')}** peak at {e.get('freq_hz')} Hz (expected near {e.get('expected_hz')} Hz) · "
                         f"{e.get('vs_normal')}× the healthy baseline · {str(e.get('strength', '')).upper()}")
            if not sensor.get("evidence"):
                st.caption("No vibration peak stands out from the healthy baseline.")
    st.markdown(f'<div class="panel-sub">Sensor: {(sensor.get("context") or {}).get("sensor", "drive_end")} &nbsp;·&nbsp; Sample rate: {rate:,} Hz &nbsp;·&nbsp; Window: {sensor.get("window_index", sig.get("window_index", "—"))}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label" style="margin-top:22px">03 / Explanation</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(data.get("explanation") or "Explanation unavailable. The rest of the result is still shown below.")
    causes = data.get("likely_causes")
    if isinstance(causes, list) and causes:
        st.markdown("**Possible causes to inspect**")
        for cause in causes:
            st.markdown(f"- {cause}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label" style="margin-top:22px">04 / Recommended maintenance actions</div>', unsafe_allow_html=True)
    citations = {c.get("id"): c for c in (data.get("citations") or []) if isinstance(c, dict) and c.get("id")}
    actions = data.get("recommended_actions")
    if not isinstance(actions, list):
        actions = []
        st.warning("Recommended actions are missing from this response.")
    for i, action in enumerate(actions, 1):
        if not isinstance(action, dict):
            continue
        st.markdown('<div class="action-card">', unsafe_allow_html=True)
        left, right = st.columns([5, 1.2], vertical_alignment="top")
        with left:
            st.markdown(f'<div class="action-title">{i:02d} &nbsp; {action.get("step", "Action details unavailable")}</div>', unsafe_allow_html=True)
        with right:
            if action.get("safety_critical"):
                st.markdown('<span class="safety">SAFETY-CRITICAL</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="chip">REVIEW</span>', unsafe_allow_html=True)
        ids = action.get("citation_ids") if isinstance(action.get("citation_ids"), list) else []
        if not ids:
            st.caption("No citations were attached to this action.")
        for cid in ids:
            citation = citations.get(cid)
            if not citation:
                st.caption(f"Source unavailable for citation: {cid}")
                continue
            title = citation.get("source_title", "Untitled source")
            page = citation.get("page")
            with st.expander(f"↗ Source: {title}" + (f" · p. {page}" if page is not None else "")):
                st.write(citation.get("excerpt") or "No excerpt supplied.")
                if citation.get("synthetic") or "synthetic" in str(cid).lower() or "mock" in str(cid).lower():
                    st.caption("Illustrative mock citation — replace with a verified source before presenting as evidence.")
                url = citation.get("url")
                if isinstance(url, str) and url.startswith(("https://", "http://")) and "example.com" not in url:
                    st.link_button("Open source document", url)
                elif url:
                    st.caption(f"Demo link: {url}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label" style="margin-top:22px">05 / Technician decision</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><div class="panel-title">Human-in-the-loop safety gate</div><div class="panel-sub">Safety-critical steps are not accepted until a person deliberately confirms them.</div>', unsafe_allow_html=True)
    request_id = data.get("request_id")
    if st.session_state.get("decision_request") != request_id:
        st.session_state["decision_request"] = request_id
        st.session_state["decision"] = None
    if data.get("needs_human_confirm"):
        st.markdown('<div class="warning">A safety-critical action is present. Confirm only after reviewing the procedure and site safety requirements.</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        confirm_clicked = st.button("✓  Confirm reviewed", type="primary", width="stretch", key="confirm_decision")
    with c2:
        escalate_clicked = st.button("↗  Escalate to specialist", width="stretch", key="escalate_decision")
    decision = "confirmed" if confirm_clicked else "escalated" if escalate_clicked else None
    if decision:
        try:
            response = {"status": "stored"} if MOCK else post_json("/confirm", {"request_id": request_id, "decision": decision})
            if response.get("status") != "stored" and response.get("decision") != decision:
                raise ValueError("The backend did not confirm that the decision was stored.")
            st.session_state["decision"] = decision
        except (requests.RequestException, ValueError, KeyError) as exc:
            st.error(f"Could not save the decision: {exc}")
    if st.session_state.get("decision") == "confirmed":
        st.success("Technician review confirmed." + (" Demo only — not saved to a backend." if MOCK else " Decision saved by backend."))
    elif st.session_state.get("decision") == "escalated":
        st.warning("Escalated for specialist review." + (" Demo only — not saved to a backend." if MOCK else " Decision saved by backend."))
    else:
        st.caption("Awaiting technician decision.")
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Model class probabilities"):
        probabilities = sensor.get("probabilities")
        if isinstance(probabilities, dict) and probabilities:
            for key, value in probabilities.items():
                label = FAULTS.get(key, {}).get("name", key.replace("_", " ").title())
                if isinstance(value, (int, float)):
                    st.write(f"**{label}** · {value:.1%}")
                    st.progress(max(0.0, min(1.0, float(value))))
        else:
            st.caption("Probability breakdown was not supplied by the API.")
    with st.expander("All sources used"):
        if citations:
            for cite in citations.values():
                page = f" · page {cite['page']}" if cite.get("page") is not None else ""
                st.write(f"**{cite.get('source_title', 'Unknown source')}**{page} · {cite.get('excerpt', 'No excerpt supplied.')}")
        else:
            st.caption("No sources were returned.")
    if MOCK:
        st.info("DEMO MODE: fault labels, confidence, citations, latency and AMD status are simulated for interface testing. The waveform is synthetic and no real model/GPU inference is performed.")


render_header()
intro_left, intro_right = st.columns([3, 1], vertical_alignment="center")
with intro_left:
    st.markdown("### Machine health console")
    st.markdown('<div class="status-line">Select a vibration recording to inspect the signal and review maintenance guidance.</div>', unsafe_allow_html=True)
with intro_right:
    st.markdown('<div style="text-align:right;color:#91a2b8;font-size:11px">TRACK 01 &nbsp; / &nbsp; INTELLIGENT INDUSTRY</div>', unsafe_allow_html=True)

try:
    rows = recordings()
    if not rows:
        st.warning("No recordings are available. Check the API or mock_data/sample.json.")
        st.stop()
    row_map = {row["recording_id"]: row for row in rows}
    ids = list(row_map)
    names = {rid: FAULTS.get(row_map[rid].get("true_fault_type"), {}).get("name", "Unknown") for rid in ids}
    default_index = 0
    if "next_recording" in st.session_state and st.session_state["next_recording"] in ids:
        default_index = ids.index(st.session_state["next_recording"])
        del st.session_state["next_recording"]
    selected = st.selectbox("RECORDING LIBRARY", ids, index=default_index,
                            format_func=lambda rid: f"{rid}   ·   {names.get(rid, 'Unknown condition')}")
    chosen = row_map[selected]
    a, b, c, d = st.columns([1.1, 1, 1, 1.2])
    a.markdown(f'<div class="metric-card"><div class="metric-label">Condition label</div><div class="metric-value" style="font-size:17px">{names.get(selected, "Unknown")}</div><div class="metric-note">{"Mock label for demo only" if MOCK else "Recorded condition (CWRU)"}</div></div>', unsafe_allow_html=True)
    b.markdown(f'<div class="metric-card"><div class="metric-label">Motor speed</div><div class="metric-value">{chosen.get("approx_rpm", "—")}</div><div class="metric-note">RPM (approx.)</div></div>', unsafe_allow_html=True)
    c.markdown(f'<div class="metric-card"><div class="metric-label">Load</div><div class="metric-value">{chosen.get("load_hp", "—")} hp</div><div class="metric-note">Motor load</div></div>', unsafe_allow_html=True)
    d.markdown(f'<div class="metric-card"><div class="metric-label">Available windows</div><div class="metric-value">{chosen.get("num_windows", "—")}</div><div class="metric-note">Signal segments</div></div>', unsafe_allow_html=True)
    last_window = max(int(chosen.get("num_windows") or 100) - 1, 0)
    window = st.slider("WINDOW (a 2,048-sample slice of the recording)", 0, last_window, min(12, last_window),
                       key=f"window_{selected}", help="Different windows give different confidence: try a few.")
    st.write("")
    run_col, next_col, hint_col = st.columns([1.15, 1, 2.8], vertical_alignment="center")
    with run_col:
        run = st.button("⌕  Analyze recording", type="primary", width="stretch")
    with next_col:
        next_clicked = st.button("Next demo recording  →", width="stretch")
    with hint_col:
        st.markdown('<div class="status-line">Demo sequence includes healthy, inner-race, outer-race and ball-fault examples.</div>', unsafe_allow_html=True)
    if next_clicked:
        current = ids.index(selected)
        st.session_state["next_recording"] = ids[(current + 1) % len(ids)]
        st.rerun()
    if run:
        try:
            with st.spinner("Stage 1/2 · Reading vibration signal…"):
                sig = signal(selected, window)
            with st.spinner("Stage 2/2 · Analyzing signal and preparing guidance… (10 to 20 s with the live LLM)"):
                result = analyze(selected, window)
            if not isinstance(result.get("sensor"), dict):
                raise ValueError("Analysis response is missing the sensor object")
            st.session_state["result"] = result
            st.session_state["signal"] = sig
            st.session_state["recording"] = selected
            st.session_state["decision_request"] = None
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            st.session_state.pop("result", None)
            st.error(f"Analysis failed: {exc}")
            if st.button("Retry analysis", type="primary"):
                st.rerun()
    if "result" in st.session_state and "signal" in st.session_state:
        active_id = st.session_state.get("recording", selected)
        if active_id in row_map:
            st.caption(f"Ground-truth label for demo evaluation only: {names.get(active_id, 'Unknown')}")
        left, right = st.columns([1, 1.08], gap="large")
        with left:
            st.markdown('<div class="section-label">Live signal preview</div>', unsafe_allow_html=True)
            st.markdown('<div class="panel"><div class="panel-title">Sensor data</div><div class="panel-sub">Vibration window loaded from selected recording</div>', unsafe_allow_html=True)
            sig = st.session_state["signal"]
            render_signal_chart(sig, key="signal_preview")
            st.markdown(f'<div class="panel-sub">ID: {active_id} &nbsp;·&nbsp; Window: {sig.get("window_index", 12)} &nbsp;·&nbsp; {sig.get("sample_rate_hz", "—")} Hz</div></div>', unsafe_allow_html=True)
        with right:
            render_result(st.session_state["result"], sig, active_id)
    else:
        st.markdown('<div class="panel" style="text-align:center;padding:38px 20px"><div style="font-size:30px;color:#69dcff">⌁</div><div class="panel-title" style="margin-top:10px">Ready to inspect a machine</div><div class="panel-sub" style="max-width:520px;margin:8px auto 0">Choose a recording above and select Analyze recording. Your fault assessment, signal chart, source-backed action list and technician decision will appear here.</div></div>', unsafe_allow_html=True)
except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
    st.error(f"Could not load recordings: {exc}")
    st.caption("Check MOCK=true for demo mode, or verify API_URL and the backend service.")

MOCK_NOTE = "<br>Mock mode uses illustrative data, synthetic signals and placeholder citations. Verify sources and connect the real model/API before presenting diagnostic claims as real." if MOCK else ""
st.markdown(f'<div class="footnote">BEARINGGUARD · DECISION SUPPORT ONLY &nbsp; | &nbsp; This interface is not a substitute for inspection by a qualified technician. Follow site lockout/tagout procedures and approved maintenance documentation. Confirm all safety-critical actions before work begins.{MOCK_NOTE}</div>', unsafe_allow_html=True)

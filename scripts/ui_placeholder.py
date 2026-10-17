"""Placeholder Streamlit UI for Bearing Fault Copilot.

Karan: replace this with your real UI in app/ui/.
Then update the CMD in the 'ui' target of the Dockerfile:
    CMD ["streamlit", "run", "app/ui/your_entry.py", ...]
"""

import os

import httpx
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8080")

st.set_page_config(page_title="Bearing Fault Copilot", page_icon="🔧", layout="wide")

st.title("🔧 Bearing Fault Copilot")
st.caption("Placeholder UI — Karan's real interface will replace this file.")

# ---- Health check --------------------------------------------------------
try:
    health = httpx.get(f"{API_URL}/health", timeout=5).json()
    status = health.get("status", "?")
    mode = health.get("mode", "?")
    if status == "ok":
        st.success(f"API is healthy — mode: **{mode}**")
    else:
        st.warning(f"API responded but status is **{status}**")
    with st.expander("Health details"):
        st.json(health)
except Exception as exc:
    st.error(f"Cannot reach API at `{API_URL}`: {exc}")
    st.info("Is the **api** service running?  Try: `docker compose up api`")
    st.stop()

st.divider()

# ---- Recordings ----------------------------------------------------------
try:
    recordings = httpx.get(f"{API_URL}/recordings", timeout=5).json()
except Exception:
    recordings = []

if not recordings:
    st.info("No recordings available (MOCK_MODE may be off and real pipeline not connected).")
    st.stop()

st.subheader("Demo recordings")
rec_map = {r["recording_id"]: r for r in recordings}
selected_id = st.selectbox("Recording", list(rec_map.keys()))
window = st.number_input("Window index", min_value=0, max_value=116, value=0)

# ---- Analyze -------------------------------------------------------------
if st.button("🔍 Analyze", type="primary"):
    with st.spinner("Running classifier → retrieval → LLM …"):
        try:
            resp = httpx.post(
                f"{API_URL}/analyze",
                json={"recording_id": selected_id, "window_index": window},
                timeout=60,
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as exc:
            st.error(f"Analysis failed: {exc}")
            st.stop()

    st.success("Analysis complete")

    # Key metrics
    sensor = result.get("sensor", {})
    uncertainty = result.get("uncertainty", {})
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fault type", sensor.get("fault_type", "—").replace("_", " ").title())
    col2.metric("Severity", sensor.get("severity", "—"))
    col3.metric("Confidence", f"{sensor.get('confidence', 0):.0%}")
    col4.metric("Uncertainty", uncertainty.get("level", "—"))

    # Explanation
    st.subheader("Explanation")
    st.write(result.get("explanation", "—"))

    # Actions
    actions = result.get("recommended_actions", [])
    if actions:
        st.subheader("Recommended actions")
        for i, action in enumerate(actions, 1):
            icon = "🔴" if action.get("safety_critical") else "🟢"
            st.markdown(f"{icon} **Step {i}:** {action.get('step', '—')}")

    # Human confirm
    if result.get("needs_human_confirm"):
        st.warning("⚠️ This analysis requires human confirmation before proceeding.")

    # Full JSON
    with st.expander("Full JSON response"):
        st.json(result)

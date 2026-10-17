"""Headless check of the screen (Streamlit AppTest):  python -m app.ui.test_ui

Always runs the mock-mode flow (no server). If UI_TEST_API is set (for example http://127.0.0.1:8080, with the API
running in MOCK_MODE=true and LLM_MOCK=true so it needs no key) it also runs the real-mode flow against that API:
load, analyze a window, confirm."""
import os
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).with_name("app.py"))


def _text(at):
    parts = ([m.value for m in at.markdown] + [c.value for c in at.caption] + [e.value for e in at.error]
             + [w.value for w in at.warning] + [s.value for s in at.success])
    return " ".join(parts)


def _button(at, label_part):
    return next(b for b in at.button if label_part in b.label)


def _run(mock, api=None):
    os.environ["MOCK"] = "true" if mock else "false"
    if api:
        os.environ["API_URL"] = api
    at = AppTest.from_file(APP, default_timeout=90).run()
    assert not at.exception and not at.error, (at.exception, [e.value for e in at.error])
    return at


def _analyze_and_confirm(at, rid, window, expect_text):
    at.selectbox[0].select(rid).run()
    at.slider[0].set_value(window).run()
    _button(at, "Analyze recording").click().run()
    assert not at.exception and not at.error, (at.exception, [e.value for e in at.error])
    t = _text(at)
    assert expect_text in t and f"Window: {window}" in t, f"analysis did not render for {rid} window {window}"
    assert "Explanation model:" in t and "Served on:" in t, "model / served-on line missing"
    _button(at, "Confirm reviewed").click().run()
    assert not at.exception and not at.error, [e.value for e in at.error]
    assert any("Technician review confirmed" in s.value for s in at.success)
    return t


def test_mock_mode_flow():
    at = _run(mock=True)
    assert "DEMO MODE" in _text(at) and len(at.selectbox[0].options) == 4
    _analyze_and_confirm(at, "OR007@6_0", 12, "OUTER RACE DETECTED")


def test_real_mode_flow_against_a_running_api():
    api = os.environ.get("UI_TEST_API")
    if not api:
        print("   (skipped: set UI_TEST_API to run the real-mode flow)")
        return
    at = _run(mock=False, api=api)
    head = next(m.value for m in at.markdown if 'class="top-pill"' in m.value)
    assert "LIVE" in head, head
    opts = at.selectbox[0].options
    assert opts and all("_3" in o for o in opts), opts  # held-out (3 hp) recordings only
    assert "Mock label for demo only" not in _text(at)
    _analyze_and_confirm(at, "OR007@6_3", 2, "OUTER RACE DETECTED")


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print("ok  ", name)
    print(f"{len(tests)} checks passed")
    sys.exit(0)

# app/ui: the screen (Streamlit)

Started from Karan's prototype. Changes for the real API: it reads our `/recordings` list and field names, shows only
held-out recordings by default, has a window slider, shows the model, "served on" and per-stage latency, shows the
vibration evidence, and accepts our `/confirm` answer.

## Run

Start the API first (see `../README.md`), then, from the repo root:

```
pip install -r app/ui/requirements.txt
copy app\ui\.env.example app\ui\.env        # macOS/Linux: cp app/ui/.env.example app/ui/.env
python -m streamlit run app/ui/app.py       # opens http://localhost:8501
```

- `MOCK=true` in `app/ui/.env`: built-in demo data, no API (the screen then says DEMO MODE; nothing on it is a real result).
- `MOCK=false`: uses the API at `API_URL` (default `http://localhost:8080`). The header shows which API parts are real.
- A real analysis takes 10 to 20 seconds (the LLM call). The screen says so while it waits.

## Check

```
python -m app.ui.test_ui                    # mock mode, no server needed
UI_TEST_API=http://127.0.0.1:8080 python -m app.ui.test_ui   # also runs the real-mode flow against a running API
```

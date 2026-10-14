# app/

API, orchestrator and user interface.

Owner: Kushal (API, AMD serving) and Karan (UI)

- `app/api/` is the backend (FastAPI). It follows `docs/contract.md`.
- Put the user interface in its own subfolder, for example `app/ui/`.

## Run the mock API (for Karan and anyone who needs data)

The mock API serves canned data in the contract shape. It needs no models, no data and no LLM key, and only
installs FastAPI (not numpy or scikit-learn). Tested with Python 3.10.

```bash
python -m venv .venv
# activate: Git Bash  source .venv/Scripts/activate | PowerShell  .venv\Scripts\Activate.ps1 | Linux/macOS  source .venv/bin/activate
pip install -r app/api/requirements.txt
python -m app                      # http://localhost:8080  (opens the interactive docs with "try it" buttons, also at /docs)
python -m app.api.test_api         # self-check, 10 checks
```

Settings (all optional, same names as `.env.example`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `MOCK_MODE` | `true` | `false` makes the data endpoints answer 501 until the real pipeline is connected |
| `API_HOST` | `127.0.0.1` | use `0.0.0.0` inside Docker |
| `API_PORT` | `8080` | |
| `CORS_ORIGINS` | `*` | comma-separated list; set it when the UI is hosted on its own domain |

PowerShell example: `$env:API_PORT = "9000"; python -m app`

## Endpoints

| Endpoint | Notes |
| --- | --- |
| `GET /health` | status per part, plus `mode` (`mock` or `real`) |
| `GET /recordings` | 40 demo recordings. `held_out: true` marks the 10 at 3 hp (the real model never trained on them) |
| `GET /signal?recording_id=...&window_index=...&max_points=512` | window 0 to 116. `sample_rate_hz` is the rate of the returned list, so `i / sample_rate_hz` is the true time |
| `POST /analyze` | body `{"recording_id": "OR007@6_3", "window_index": 2}`, returns the final answer (contract section 3) |
| `POST /confirm` | body `{"request_id": "req-0001", "decision": "confirmed"}` or `"escalated"`. The request id must come from an earlier `/analyze` |

Errors: unknown recording or request id is 404, window out of range or bad body is 422.

## What the mock does (so the screen can be built against every state)

- Deterministic: the same recording and window always give the same answer.
- Always labeled: explanations start with `[MOCK]`, `meta.model` is `mock`, citations point to `example.com`.
  Do not screenshot mock output as if it were real.
- The classifier "predicts" the true label, with a confidence that varies by window so every uncertainty level appears:

| Try this | What you get |
| --- | --- |
| `OR007@6_0`, window 12 | the exact sample from `docs/contract.md` (medium uncertainty) |
| `OR007@6_3`, window 0 | outer race, **high** uncertainty (57%): hedged text, "arrange a manual inspection" first |
| `OR007@6_3`, window 2 | outer race, **medium** uncertainty (71%) |
| `OR007@6_3`, window 1 | outer race, **low** uncertainty (95%) |
| `Normal_3`, window 1 | healthy bearing: no causes, no safety-critical step, `needs_human_confirm` false |
| `Normal_3`, window 9 | healthy but **high** uncertainty (48%): manual inspection suggested |

- `sensor.evidence` (Harshit's optional field) is present in the mock. It is empty for healthy windows. The UI must cope with it
  being missing or empty.
- `uncertainty.level` comes from the confidence: high below 0.60, medium 0.60 to 0.95, low from 0.95
  (`app/api/uncertainty.py`).
- `needs_human_confirm` is true when any action is `safety_critical` or the uncertainty is high.
- The latency numbers are fixed placeholders.

Everything outside `/health`, `/recordings`, `/signal`, `/analyze` and `/confirm` is not built yet: retrieval, the LLM call
and the real sensor hookup come next.

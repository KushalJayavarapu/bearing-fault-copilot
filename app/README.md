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
python -m app.api.test_all         # every self-check (41 checks, no key or network needed)
```

Settings (all optional, same names as `.env.example`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `MOCK_MODE` | `true` | `false` makes the data endpoints answer 501 until the real pipeline is connected |
| `API_HOST` | `127.0.0.1` | use `0.0.0.0` inside Docker |
| `API_PORT` | `8080` | |
| `LLM_MOCK` | same as `MOCK_MODE` | `false` (with `MOCK_MODE=true`) gets the explanation from the real LLM, see below |
| `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | none | the OpenAI-compatible LLM server; put them in `.env` (never commit it) |
| `LLM_SERVED_ON` | `unknown` | what to show as `meta.served_on`; set it to what really serves the model |
| `LLM_MAX_CONCURRENT` | `2` | simultaneous LLM calls from this app (the team shares one key) |
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

## Real LLM explanation (once the key is unlocked)

1. Copy `.env.example` to `.env` and fill in `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. `.env` is gitignored. Never paste the key in the chat.
2. Test the connection: `python -m app.api.llm_smoke`. It lists the models, sends one prompt, checks JSON mode, and prints a line to post
   in the team chat (it never prints the key).
3. In `.env` set `LLM_MOCK=false` and restart `python -m app`. `/analyze` now gets its explanation from the real LLM.
   The sensor result and the reference passages are still mock/stub until those parts are connected (`/health` shows `mode: mixed`).

How the LLM is used (`app/api/orchestrator.py`, `app/api/prompt.py`):

- The model writes only the explanation, causes and actions. Sensor result, uncertainty, citations, `needs_human_confirm` and `meta`
  are built by our code, so the model cannot fake them.
- Citations only come from retrieved passages. An action the passages do not support is dropped. A step that sounds like physical work
  (stop, isolate, open, remove, replace, inspect the bearing) is always `safety_critical`, whatever the model says.
- High uncertainty: the text is hedged and "arrange a manual inspection" comes first.
- Vibration evidence that disagrees with the classifier is shown in the note, and uncertainty cannot then be `low`.
- No retrieved passages: the LLM is not asked. LLM down or an unusable answer (after one repair try): the answer shows the sensor result
  and a manual inspection, never an error page. 429 and 5xx are retried with backoff.
- The reference passages are untrusted text: the prompt tells the model to ignore instructions inside them.

Still to come: connecting the real retrieval and the real sensor (`MOCK_MODE=false`), which today answers 501.

# Bearing Fault Copilot

A "detect, explain, act" assistant for factory bearings, built for the AMD Developer Hackathon: ACT III (Track 1, Intelligent Industry).

Pick a vibration recording. The app tells you what is probably wrong with the bearing, why, and what to do next. It says how sure it is and cites where each recommendation comes from. Anything that means working on the machine is flagged and needs a person's confirmation.

```
vibration window ─► classifier ─► retrieval over ─► LLM on AMD (Token Factory) ─► answer + citations ─► human confirms
 (CWRU recording)   fault, size,   maintenance      explanation, causes,            uncertainty shown,    safety-critical
                    confidence,    notes             actions                         safety steps flagged  steps
                    evidence
```

## What is real and what is not

| Part | Status |
| --- | --- |
| Fault classifier (`sensor/`) | Real. Random forests on 28 vibration features, trained on the CWRU bearing dataset. |
| Retrieval (`rag/`) | Real. Hybrid keyword + embedding search (BM25 and `BAAI/bge-small-en-v1.5`) over our knowledge base. |
| LLM | Real. `DeepSeek-V4-Flash-Vision-Exp` through AMD Token Factory (an OpenAI-compatible service on AMD GPUs). **We call this service; we did not host or fine-tune the model.** |
| Knowledge base (`data/`) | **Team-written reference notes**, a curated table mapping CWRU fault locations to damage modes and actions, and **36 synthetic maintenance-log entries** (marked `[Synthetic example]` in answers). It is not a copy of any vendor manual and carries no vendor page numbers, so answers show no page numbers. |
| Human confirmation | The UI asks a person to confirm or escalate before a safety-critical step is accepted. The decision is recorded by the API; nothing is actually executed on a machine. |

## Run it

Needs Python 3.10 or newer. Two modes:

### 1. Mock mode (2 minutes, nothing to download, no key)

Canned sensor results and stub passages. Good for looking around, and what the tests use.

```bash
python -m venv .venv
source .venv/Scripts/activate        # PowerShell: .venv\Scripts\Activate.ps1
pip install -r app/api/requirements.txt -r app/ui/requirements.txt
cp .env.example .env                 # MOCK_MODE=true is the default
python -m app                        # API on http://localhost:8080 (docs at /docs)
```

In a second terminal:

```bash
streamlit run app/ui/app.py          # set MOCK=false in app/ui/.env to talk to the API; MOCK=true needs no API
```

### 2. Real mode (real classifier, real retrieval, real LLM)

```bash
pip install -r sensor/requirements.txt -r rag/requirements.txt -r app/api/requirements.txt -r app/ui/requirements.txt
python -m sensor.build               # downloads CWRU (~140 MB), checks SHA-256, trains the models
python -m data.fetch_guides          # writes the local knowledge texts
python -m rag.build                  # builds the index (first run downloads the embedding model)
```

In `.env` set `MOCK_MODE=false`, `LLM_MOCK=false` and `LLM_API_KEY` (from your Token Factory page; never commit it). Then `python -m app`. The log should end with `warm-up done ... sensor=ok retrieval=ok`, and `GET /health` should report `llm: live`. Details, troubleshooting and the model comparison are in [`app/README.md`](app/README.md).

An LLM call takes about 7 to 15 seconds, so the UI shows a spinner. If the LLM is down or returns something unusable, the API still answers: sensor result, uncertainty and citations are shown, with a plain "explanation unavailable" text.

### Tests

```bash
python -m app.api.test_all           # API, LLM client, orchestrator, real-mode wiring (no key, no network)
python -m app.ui.test_ui             # UI flows
python -m sensor.test_sensor         # classifier (after sensor.build)
```

## How we try to keep it honest

- **The LLM writes only the explanation, likely causes and recommended actions.** The sensor result, uncertainty, citations, confirm flags and metadata are filled in by code, not by the model.
- **No invented sources.** Any citation id the model makes up is dropped. Page numbers are hidden unless `CITE_PAGES=true`, because our notes have no real page numbers.
- **Safety flag can only go up.** If a recommended action involves stopping, isolating, opening or restarting the machine, code marks it `safety_critical` even when the model did not.
- **Uncertainty is shown, not hidden.** Below 0.60 classifier confidence the answer says the fault is only a possibility and puts "inspect manually" first. Disagreement between the classifier and the vibration evidence lifts a "low" uncertainty to "medium".
- **No passages, no LLM call.** If retrieval finds nothing, the model is not asked to answer from memory.
- Data shapes between the parts are fixed in [`docs/contract.md`](docs/contract.md).

## What the classifier can and cannot do

All numbers are measured and committed in [`sensor/results/`](sensor/results/); the handover is in [`sensor/STATUS.md`](sensor/STATUS.md).

- On a **motor load it has not seen** (leave-one-load-out): fault-type accuracy 0.990, macro-F1 0.989.
- Demo model on the held-out 3 hp recordings: accuracy 0.964; 5.2% of windows are below 0.60 confidence.
- On **bearings of a fault size it has not seen**, accuracy drops to 1.000 / 0.497 / 0.715 (small / medium / large). For outer-race faults at other clock positions, 0.499 / 0.399.
- **The 99% means unseen motor load, not unseen bearing.** CWRU reuses one physical bearing per fault at every load.
- Lab rig, faults seeded by EDM. This is not evidence it works on a real factory floor.
- The vibration-evidence check is weak for ball faults (empty for 95.5% of ball windows).

The retrieval hit rates in [`rag/README.md`](rag/README.md) (10/10, 12/12, 18/18) come from questions written by our own team, not an independent benchmark.

## Repo layout

| Folder | What lives here |
| --- | --- |
| `sensor/` | Fault classifier, evaluation, CWRU download and build |
| `rag/` | Retrieval pipeline |
| `app/api/` | FastAPI service, orchestrator, LLM client, prompt, tests |
| `app/ui/` | Streamlit frontend |
| `data/` | Knowledge notes, synthetic logs, download scripts (no raw data) |
| `docs/` | Data contract, dependency graph, demo script, submission text |

## Team

Kushal (architecture, integration, AMD serving), Harshit (sensor classifier), Santos (retrieval), Atharva (data and knowledge base), Karan (frontend), Karthiik (Docker, video, submission).

## Data and citations

- **CWRU Bearing Dataset:** vibration data courtesy of the Case Western Reserve University Bearing Data Center (https://engineering.case.edu/bearingdatacenter), collected under the direction of Prof. Kenneth A. Loparo.
  > K. A. Loparo, *Bearing Vibration Data*, Case Western Reserve University Bearing Data Center Website.
- Fault-frequency analysis follows W. A. Smith and R. B. Randall, "Rolling element bearing diagnostics using the Case Western Reserve University data: a benchmark study", *Mechanical Systems and Signal Processing* 64-65 (2015).
- CWRU has no licence. The raw data is not in this repo (see [`data/README.md`](data/README.md)); **do not push a Docker image containing it to a public registry.**

## Working on this repo

- Nobody pushes to `main`. Branch as `area/yourname-short-task`, open a PR, get one approval.
- Never commit secrets (`.env`), raw data, source PDFs or model weights.

## Licence

MIT. See [LICENSE](LICENSE).

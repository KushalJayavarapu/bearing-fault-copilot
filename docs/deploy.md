# Deploying Bearing Fault Copilot

Owner: Karthiik (delivery and hosting)

---

## Prerequisites

- **Docker** ≥ 24.0 and **Docker Compose** ≥ 2.24 (comes with Docker Desktop)
- No GPU, API keys, or raw data needed for mock mode

---

## Quick start (mock mode — works on a fresh clone)

```bash
git clone <repo-url> && cd bearing-fault-copilot

# Optional: copy and customise environment variables
cp .env.example .env

# Build and start both services
docker compose up --build
```

| Service | URL | What it does |
|---------|-----|--------------|
| **api** | [http://localhost:8080](http://localhost:8080) | FastAPI orchestrator (Swagger docs at `/docs`) |
| **ui**  | [http://localhost:8501](http://localhost:8501) | Streamlit interface |

The API starts in `MOCK_MODE=true` by default: every endpoint returns canned data
in the contract shape, no models or LLM key needed.

### Verify it works

```bash
# API health
curl http://localhost:8080/health
# → {"status":"ok","mode":"mock","parts":{"api":"ok","sensor":"mock","retrieval":"mock","llm":"mock"}}

# Streamlit should show "API is healthy" at http://localhost:8501
```

---

## Switching to the real pipeline

1. **Set up environment variables** — copy `.env.example` to `.env` and fill in:
   ```ini
   MOCK_MODE=false
   LLM_MOCK=false
   LLM_BASE_URL=http://your-amd-server:8000/v1
   LLM_API_KEY=rc-your-real-key-here
   LLM_MODEL=your-model-name
   RETRIEVER_MODE=real
   ```

2. **Prepare data** (downloads CWRU recordings, trains models, builds RAG index):
   ```bash
   docker compose run --rm api bash scripts/prepare_data.sh
   ```

3. **Start services**:
   ```bash
   docker compose up --build
   ```

> [!IMPORTANT]
> If `RETRIEVER_MODE=real` and the RAG index (`rag/index/passages.json`) has not
> been built, the API will refuse to start with a clear error message.

---

## Architecture

```
┌──────────────────────────┐     ┌──────────────────────────┐
│  ui  (Streamlit :8501)   │────▶│  api  (FastAPI :8080)    │
│  scripts/ui_placeholder  │     │  python -m app           │
│  depends_on: api healthy │     │  healthcheck: /health    │
└──────────────────────────┘     └──────────────────────────┘
```

Both services share one Docker image (built from different Dockerfile targets).
The `api` service has a healthcheck on `GET /health`; the `ui` service waits
for it to become healthy before starting.

---

## Environment variables

All settings come from environment variables. See [`.env.example`](../.env.example)
for the full list with comments. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MOCK_MODE` | `true` | `true` = canned data, no deps; `false` = real pipeline |
| `LLM_MOCK` | same as `MOCK_MODE` | `false` = real LLM explanations |
| `RETRIEVER_MODE` | `mock` | `real` = requires built RAG index; `mock` = stub passages |
| `API_HOST` | `0.0.0.0` | Bind address for the API |
| `API_PORT` | `8080` | API listen port |
| `UI_PORT` | `8501` | Streamlit listen port |
| `API_URL` | `http://localhost:8080` | URL the UI uses to reach the API |
| `PORT` | — | Generic port (hosting platforms); falls back to `API_PORT` |
| `LLM_BASE_URL` | — | OpenAI-compatible endpoint |
| `LLM_API_KEY` | — | API key (never commit) |
| `LLM_MODEL` | — | Model name |

---

## Single-container hosting (Render, Railway, Fly.io)

Many hosting platforms run one container per service and set the `PORT` environment
variable. To deploy the API on such a platform:

1. **Set the build target** to `api`:
   ```
   Docker build target: api
   ```
   Or build and push:
   ```bash
   docker build --target api -t your-registry/bearing-api:latest .
   docker push your-registry/bearing-api:latest
   ```

2. **Set environment variables** on the platform dashboard:
   ```
   PORT=<platform-assigned>
   MOCK_MODE=true          # or false with real keys
   RETRIEVER_MODE=mock     # or real after running prepare_data.sh
   ```
   The entrypoint maps `PORT` → `API_PORT` automatically.

3. **Health check path:** `/health`

4. **For the UI**, deploy the `ui` target as a separate service and set
   `API_URL` to the API service's internal URL.

---

## Developing locally without Docker

```bash
# Terminal 1 — API
pip install -r app/api/requirements.txt
python -m app                    # http://localhost:8080/docs

# Terminal 2 — UI (placeholder)
pip install streamlit httpx
streamlit run scripts/ui_placeholder.py
```

---

## Rebuilding after teammates' changes

| When | Command |
|------|---------|
| **Anyone** changes Python code | `docker compose up --build` |
| **Santos** adds `rag/requirements.txt` | Uncomment the two lines in the Dockerfile, then rebuild |
| **Karan** pushes real UI in `app/ui/` | Update the `CMD` in the `ui` Dockerfile target to point to his entry file |
| **Data or model changes** | `docker compose run --rm api bash scripts/prepare_data.sh`, then restart |

---

## TODOs for teammates

| Who | What | Why |
|-----|------|-----|
| **Santos** | Create `rag/requirements.txt` listing `fastembed`, `rank-bm25`, `numpy`, `pydantic` | These packages are imported in `rag/indexer.py` and `rag/models.py` but not declared in any requirements file |
| **Santos** | Uncomment the two `rag/requirements.txt` lines in the Dockerfile after creating the file | Enables real retrieval in Docker |
| **Karan** | Push the Streamlit UI to `app/ui/` and update the `ui` CMD in the Dockerfile | The current `scripts/ui_placeholder.py` is a minimal stand-in |
| **Atharva** | Verify `python -m data.fetch_guides` works headlessly (no browser/tty) | Called by `scripts/prepare_data.sh` inside Docker |
| **Kushal** | Wire `RETRIEVER_MODE` into the orchestrator so `real` mode calls Santos's retriever instead of the stub | Currently `app/api/main.py` always uses `retrieval_stub.py`; the `RETRIEVER_MODE` guard in the entrypoint only checks for the index file |

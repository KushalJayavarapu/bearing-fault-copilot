# ---- Base stage: shared dependencies and source ----
FROM python:3.12-slim AS base

LABEL maintainer="Kartik (delivery)" \
      project="bearing-fault-copilot" \
      hackathon="AMD Developer Hackathon ACT III - Track 1"

WORKDIR /app

# Install Python dependencies from the existing requirements files.
# Each sub-team owns their own requirements; we only consume them here.
COPY app/api/requirements.txt /tmp/req-api.txt
COPY sensor/requirements.txt  /tmp/req-sensor.txt
COPY app/ui/requirements.txt  /tmp/req-ui.txt
RUN pip install --no-cache-dir \
        -r /tmp/req-api.txt \
        -r /tmp/req-sensor.txt \
        -r /tmp/req-ui.txt \
    && rm /tmp/req-*.txt

# TODO(Santos): Create rag/requirements.txt listing fastembed, rank-bm25,
#   numpy, pydantic.  Then uncomment the two lines below:
# COPY rag/requirements.txt /tmp/req-rag.txt
# RUN pip install --no-cache-dir -r /tmp/req-rag.txt && rm /tmp/req-rag.txt

# Pre-download the fastembed embedding model so the first request is fast.
# Harmless no-op when fastembed is not installed.
RUN python -c "import importlib.util; exit(0) if not importlib.util.find_spec('fastembed') else (__import__('fastembed').TextEmbedding('BAAI/bge-small-en-v1.5'), print('fastembed model cached'))"

# Copy application source (respects .dockerignore)
COPY . .

# Make helper scripts executable
RUN chmod +x scripts/entrypoint.sh scripts/prepare_data.sh

# Shared entrypoint: RETRIEVER_MODE guard + PORT fallback
ENTRYPOINT ["/app/scripts/entrypoint.sh"]


# ---- API service target ----
FROM base AS api
EXPOSE 8080
# python -m app reads API_HOST and API_PORT from the environment
CMD ["python", "-m", "app"]


# ---- UI service target ----
FROM base AS ui
EXPOSE 8501
CMD ["sh", "-c", "exec streamlit run app/ui/app.py --server.address=0.0.0.0 --server.port=${UI_PORT:-8501} --server.headless=true --browser.gatherUsageStats=false"]

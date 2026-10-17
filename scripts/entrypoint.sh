#!/bin/sh
set -e

# ---------------------------------------------------------------------------
# Entrypoint for Bearing Fault Copilot containers.
#
# 1. Maps the generic PORT variable to API_PORT (common on hosting platforms).
# 2. Fails fast if RETRIEVER_MODE=real but the RAG index has not been built.
# 3. Passes control to the service command (uvicorn / streamlit).
# ---------------------------------------------------------------------------

# Support generic PORT variable (e.g. Render, Railway, Heroku set PORT)
export API_PORT="${API_PORT:-${PORT:-8080}}"

# --- RETRIEVER_MODE guard --------------------------------------------------
# If the operator explicitly asked for real retrieval, refuse to start without
# a built index.  This catches misconfiguration early instead of silently
# serving mock passages when the intent was real ones.
if [ "${RETRIEVER_MODE:-mock}" = "real" ]; then
    if [ ! -f /app/rag/index/passages.json ]; then
        echo "════════════════════════════════════════════════════════════"
        echo "FATAL: RETRIEVER_MODE=real but rag/index/passages.json"
        echo "       is missing.  The RAG search index has not been built."
        echo ""
        echo "Fix — pick one:"
        echo "  1. Build the index first:"
        echo "       docker compose run --rm api python -m rag.build"
        echo "  2. Or set RETRIEVER_MODE=mock in your .env"
        echo "════════════════════════════════════════════════════════════"
        exit 1
    fi
fi

# Hand off to the CMD (uvicorn, streamlit, or whatever was passed)
exec "$@"

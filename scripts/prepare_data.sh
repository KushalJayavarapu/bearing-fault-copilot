#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Optional data-preparation script for Bearing Fault Copilot.
#
# Downloads CWRU vibration data, trains the sensor model, fetches guide texts
# and builds the RAG search index.  Skipped entirely when MOCK_MODE=true
# (the default), so "docker compose up" works on a fresh clone with no data.
#
# Usage:
#   # Inside a running container:
#   docker compose run --rm api bash scripts/prepare_data.sh
#
#   # Or set MOCK_MODE=false in .env and call it before starting services.
# ---------------------------------------------------------------------------

MOCK="${MOCK_MODE:-${MOCK:-true}}"

if [ "$MOCK" = "true" ]; then
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  MOCK_MODE=true — skipping data preparation.           ║"
    echo "║  Set MOCK_MODE=false in .env to use the real pipeline. ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    exit 0
fi

echo ""
echo "=== Step 1/3: CWRU data download + sensor model training ==="
echo "    Command: python -m sensor.build"
python -m sensor.build

echo ""
echo "=== Step 2/3: Fetch and prepare guide texts ================="
echo "    Command: python -m data.fetch_guides"
# TODO(Atharva): Confirm this runs headlessly in Docker (no browser, no tty).
python -m data.fetch_guides || {
    echo "WARNING: data.fetch_guides failed."
    echo "  The RAG index will be incomplete (no guide texts)."
    echo "  Bridge table and synthetic logs are still available."
}

echo ""
echo "=== Step 3/3: Build RAG search index ========================"
echo "    Command: python -m rag.build"
python -m rag.build

echo ""
echo "=== Data preparation complete ==============================="
echo "  You can now start with MOCK_MODE=false and RETRIEVER_MODE=real."

#!/usr/bin/env python3
"""Docker healthcheck for the API service.

Called by the compose healthcheck directive:
    test: ["CMD", "python", "/app/scripts/healthcheck.py"]

Exits 0 if GET /health returns HTTP 200, exits 1 otherwise.
Reads API_PORT from the environment (default 8080).
"""
import os
import sys
import urllib.request

try:
    port = os.environ.get("API_PORT", "8080")
    urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5)
except Exception:
    sys.exit(1)

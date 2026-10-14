"""Run the API:  python -m app   (docs at http://localhost:8080/docs)

Reads .env (if present), API_HOST (default 127.0.0.1; use 0.0.0.0 inside Docker) and API_PORT (default 8080).
"""
import os

import uvicorn

from .api.envfile import load_env

if __name__ == "__main__":
    load_env()  # values from .env, before the API reads its settings
    uvicorn.run("app.api.main:app", host=os.environ.get("API_HOST", "127.0.0.1"),
                port=int(os.environ.get("API_PORT", "8080")))

"""Load KEY=VALUE lines from the repo's .env into the environment (variables already set win). No dependency.

Supported: comments on their own line, optional quotes around the value. Not supported: comments after a value.
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_env(path=None) -> bool:
    path = Path(path) if path else REPO / ".env"
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)
    return True

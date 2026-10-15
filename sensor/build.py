"""One command for a fresh clone or a Docker build: python -m sensor.build

1. Downloads the 40 recordings the model uses (not the stretch-test files) into data/raw/cwru/ (or SENSOR_DATA_DIR),
   resuming cut-off transfers, and verifies every file against sensor/cwru_manifest.json (bytes + SHA-256).
   Any mismatch stops the build; a truncated file is never used.
2. Trains the models (default demo model + the all-data model, about 5 s) unless current ones already exist.
Rerunning when everything is in place only re-checks hashes and exits (a few seconds).

python -m sensor.build --runtime-only DIR
    Copies just what the default demo model needs at runtime into DIR: the 10 held-out 3 hp recordings
    (34.2 MB, hash-checked). The healthy baseline for evidence is inside the model file, so no Normal_0-2
    files are needed. For a multi-stage Dockerfile: build in a builder stage, then copy the demo model file and DIR.
"""
import shutil
import sys
import time

import joblib

from pathlib import Path

from .data_loading import DATA_DIR, RECORDINGS, download, verify
from .train import DEMO_TEST_LOAD, FINAL_VARIANT, MODEL_PATHS, train_all

RUNTIME_RECORDINGS = {rid: m for rid, m in RECORDINGS.items() if m["load_hp"] == DEMO_TEST_LOAD}


def runtime_only(dest):
    """Copy the 10 held-out recordings (verified) into dest. Returns total bytes."""
    download(RUNTIME_RECORDINGS)
    dest.mkdir(parents=True, exist_ok=True)
    total = 0
    for m in RUNTIME_RECORDINGS.values():
        target = dest / f"{m['file']}.mat"
        shutil.copyfile(DATA_DIR / target.name, target)
        problem = verify(target, m["file"])
        if problem:
            raise RuntimeError(problem)
        total += target.stat().st_size
    return total


def models_current():
    try:
        return all({"normal_env_p99", "cols"} <= set(m := joblib.load(p)) and m["variant"] == FINAL_VARIANT
                   for p in MODEL_PATHS.values())
    except (OSError, EOFError, KeyError, ValueError):
        return False


if __name__ == "__main__":
    if "--runtime-only" in sys.argv:
        dest = Path(sys.argv[sys.argv.index("--runtime-only") + 1])
        total = runtime_only(dest)
        print(f"runtime data: {len(RUNTIME_RECORDINGS)} held-out recordings, {total / 1e6:.1f} MB, verified -> {dest}")
        sys.exit()
    t0 = time.perf_counter()
    fetched = download(RECORDINGS)
    print(f"data: {len(RECORDINGS)} recordings verified against cwru_manifest.json in {DATA_DIR} "
          f"({fetched} downloaded, {time.perf_counter() - t0:.1f} s)")
    t1 = time.perf_counter()
    if fetched == 0 and models_current():
        print("models: up to date, nothing to do (python -m sensor.train to force a retrain)")
    else:
        train_all()
        print(f"models: trained in {time.perf_counter() - t1:.1f} s")
    print(f"build done in {time.perf_counter() - t0:.1f} s")

"""One command for a fresh clone or a Docker build: python -m sensor.build

1. Downloads the 40 recordings the model uses (not the stretch-test files) into data/raw/cwru/ (or SENSOR_DATA_DIR),
   resuming cut-off transfers, and verifies every file against sensor/cwru_manifest.json (bytes + SHA-256).
   Any mismatch stops the build; a truncated file is never used.
2. Trains the models (default demo model + the all-data model, about 5 s) unless current ones already exist.
Rerunning when everything is in place only re-checks hashes and exits (a few seconds).
"""
import time

import joblib

from .data_loading import DATA_DIR, RECORDINGS, download
from .train import FINAL_VARIANT, MODEL_PATHS, train_all


def models_current():
    try:
        return all({"normal_env_p99", "cols"} <= set(m := joblib.load(p)) and m["variant"] == FINAL_VARIANT
                   for p in MODEL_PATHS.values())
    except (OSError, EOFError, KeyError, ValueError):
        return False


if __name__ == "__main__":
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

"""CWRU 12k drive-end recordings: table, fallback downloader, loader, windowing.

Data dir: data/raw/cwru/ in the repo (gitignored, Atharva's area). Override with the SENSOR_DATA_DIR env var,
or --data-dir PATH on the command line. Files are <number>.mat.

python -m sensor.data_loading [--download] [--data-dir PATH]
"""
import http.client
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.io import loadmat

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("SENSOR_DATA_DIR", REPO / "data" / "raw" / "cwru"))
URL = "https://engineering.case.edu/sites/default/files/{}.mat"
SAMPLE_RATE_HZ = 12000
WINDOW = 2048
OVERLAP = 0.5

LOADS = {0: 1797, 1: 1772, 2: 1750, 3: 1730}  # hp -> nominal rpm (fallback only)
# (id prefix, fault_type, severity, file numbers at 0/1/2/3 hp)
CONDITIONS = [
    ("Normal", "normal", "none", [97, 98, 99, 100]),
    ("IR007", "inner_race", "small", [105, 106, 107, 108]),
    ("IR014", "inner_race", "medium", [169, 170, 171, 172]),
    ("IR021", "inner_race", "large", [209, 210, 211, 212]),
    ("B007", "ball", "small", [118, 119, 120, 121]),
    ("B014", "ball", "medium", [185, 186, 187, 188]),
    ("B021", "ball", "large", [222, 223, 224, 225]),
    ("OR007@6", "outer_race", "small", [130, 131, 132, 133]),
    ("OR014@6", "outer_race", "medium", [197, 198, 199, 200]),
    ("OR021@6", "outer_race", "large", [234, 235, 236, 237]),
]
RECORDINGS = {
    f"{prefix}_{hp}": {"file": num, "condition": prefix, "fault_type": ft, "severity": sev, "load_hp": hp}
    for prefix, ft, sev, nums in CONDITIONS
    for hp, num in enumerate(nums)
}

# Stretch test set only, never trained on: outer race at 3 and 12 o'clock (0.014 has no such files at 12k DE).
OR_STRETCH = {
    f"OR{size}@{pos}_{hp}": {"file": num, "condition": f"OR{size}@{pos}", "fault_type": "outer_race",
                             "severity": sev, "load_hp": hp}
    for size, sev, pos, nums in [("007", "small", 3, [144, 145, 146, 147]), ("007", "small", 12, [156, 158, 159, 160]),
                                 ("021", "large", 3, [246, 247, 248, 249]), ("021", "large", 12, [258, 259, 260, 261])]
    for hp, num in enumerate(nums)
}
ALL_FILES = RECORDINGS | OR_STRETCH


def _fetch(url, dest, tries=20):
    """Download with resume: the CWRU server cuts each transfer after ~3 s, so keep asking for the rest
    (HTTP Range) until the file reaches its full size. Writes to .part and renames only when complete."""
    part = dest.with_suffix(".part")
    part.unlink(missing_ok=True)
    total = None
    for _ in range(tries):
        have = part.stat().st_size if part.exists() else 0
        req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if have else {})
        try:
            with urllib.request.urlopen(req, timeout=60) as r, open(part, "ab" if r.status == 206 else "wb") as f:
                total = total or int(r.headers["Content-Range"].split("/")[1] if r.status == 206 else r.headers["Content-Length"])
                shutil.copyfileobj(r, f)
        except (urllib.error.URLError, http.client.IncompleteRead, OSError):
            pass  # keep what arrived, resume on the next try
        if total and part.exists() and part.stat().st_size == total:
            part.replace(dest)
            return
    part.unlink(missing_ok=True)
    raise RuntimeError(f"{dest.name}: incomplete after {tries} tries; rerun to retry")


def download_all():
    """Fallback downloader until Atharva's script exists. Skips files already present."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for meta in ALL_FILES.values():
        path = DATA_DIR / f"{meta['file']}.mat"
        if not path.exists():
            print("downloading", path.name)
            _fetch(URL.format(meta["file"]), path)


@lru_cache(maxsize=None)
def load_recording(recording_id):
    """Return (signal float64 1-D, rpm float). No per-file normalisation, on purpose."""
    meta = ALL_FILES[recording_id]
    mat = loadmat(DATA_DIR / f"{meta['file']}.mat")
    # Some files hold several *_DE_time vars (e.g. 99.mat also has X098); take the one matching the file number.
    mine = [k for k in mat if (m := re.match(r"X(\d+)", k)) and int(m.group(1)) == meta["file"]]
    key = next(k for k in mine if k.endswith("DE_time"))  # StopIteration = wrong file, fail loudly
    rpm_keys = [k for k in mine if k.endswith("RPM")]
    rpm = float(np.ravel(mat[rpm_keys[0]])[0]) if rpm_keys else float(LOADS[meta["load_hp"]])
    return np.ravel(mat[key]).astype(np.float64), rpm


def n_windows(n_samples, window=WINDOW, overlap=OVERLAP):
    step = int(window * (1 - overlap))
    return (n_samples - window) // step + 1


def window_slice(signal, index, window=WINDOW, overlap=OVERLAP):
    if not 0 <= index < n_windows(len(signal), window, overlap):
        raise IndexError(f"window_index {index} out of range (0..{n_windows(len(signal), window, overlap) - 1})")
    start = index * int(window * (1 - overlap))
    return signal[start:start + window]


def windows(signal, window=WINDOW, overlap=OVERLAP):
    step = int(window * (1 - overlap))
    return np.lib.stride_tricks.sliding_window_view(signal, window)[::step]


if __name__ == "__main__":
    if "--data-dir" in sys.argv:
        DATA_DIR = Path(sys.argv[sys.argv.index("--data-dir") + 1])
    if "--download" in sys.argv:
        download_all()
    print(f"{'id':<12}{'file':>5}{'samples':>9}{'rpm':>7}{'windows':>8}  label")
    for rid, meta in RECORDINGS.items():
        sig, rpm = load_recording(rid)
        print(f"{rid:<12}{meta['file']:>5}{len(sig):>9}{rpm:>7.0f}{n_windows(len(sig)):>8}  {meta['fault_type']}/{meta['severity']}")
    print(len(RECORDINGS), "recordings loaded from", DATA_DIR)

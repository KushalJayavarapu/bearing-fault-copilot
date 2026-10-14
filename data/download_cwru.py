"""
CWRU Bearing Dataset Downloader and Validator
Downloads the 40 standard 12 kHz drive end recordings + normal baseline recordings
from the Case Western Reserve University Bearing Data Center.
"""

import argparse
import csv
import os
import sys
import urllib.request
from pathlib import Path

try:
    import scipy.io
except ImportError:
    scipy.io = None

BASE_URL = "https://engineering.case.edu/sites/default/files"

INDEX_DATA = [
    {"file_number": 97, "condition": "Normal_0", "fault_type": "normal", "fault_diameter_in": "", "severity": "none", "load_hp": 0, "approx_rpm": 1797},
    {"file_number": 98, "condition": "Normal_1", "fault_type": "normal", "fault_diameter_in": "", "severity": "none", "load_hp": 1, "approx_rpm": 1772},
    {"file_number": 99, "condition": "Normal_2", "fault_type": "normal", "fault_diameter_in": "", "severity": "none", "load_hp": 2, "approx_rpm": 1750},
    {"file_number": 100, "condition": "Normal_3", "fault_type": "normal", "fault_diameter_in": "", "severity": "none", "load_hp": 3, "approx_rpm": 1730},
    {"file_number": 105, "condition": "IR007_0", "fault_type": "inner_race", "fault_diameter_in": "0.007", "severity": "small", "load_hp": 0, "approx_rpm": 1797},
    {"file_number": 106, "condition": "IR007_1", "fault_type": "inner_race", "fault_diameter_in": "0.007", "severity": "small", "load_hp": 1, "approx_rpm": 1772},
    {"file_number": 107, "condition": "IR007_2", "fault_type": "inner_race", "fault_diameter_in": "0.007", "severity": "small", "load_hp": 2, "approx_rpm": 1750},
    {"file_number": 108, "condition": "IR007_3", "fault_type": "inner_race", "fault_diameter_in": "0.007", "severity": "small", "load_hp": 3, "approx_rpm": 1730},
    {"file_number": 118, "condition": "B007_0", "fault_type": "ball", "fault_diameter_in": "0.007", "severity": "small", "load_hp": 0, "approx_rpm": 1797},
    {"file_number": 119, "condition": "B007_1", "fault_type": "ball", "fault_diameter_in": "0.007", "severity": "small", "load_hp": 1, "approx_rpm": 1772},
    {"file_number": 120, "condition": "B007_2", "fault_type": "ball", "fault_diameter_in": "0.007", "severity": "small", "load_hp": 2, "approx_rpm": 1750},
    {"file_number": 121, "condition": "B007_3", "fault_type": "ball", "fault_diameter_in": "0.007", "severity": "small", "load_hp": 3, "approx_rpm": 1730},
    {"file_number": 130, "condition": "OR007@6_0", "fault_type": "outer_race", "fault_diameter_in": "0.007", "severity": "small", "load_hp": 0, "approx_rpm": 1797},
    {"file_number": 131, "condition": "OR007@6_1", "fault_type": "outer_race", "fault_diameter_in": "0.007", "severity": "small", "load_hp": 1, "approx_rpm": 1772},
    {"file_number": 132, "condition": "OR007@6_2", "fault_type": "outer_race", "fault_diameter_in": "0.007", "severity": "small", "load_hp": 2, "approx_rpm": 1750},
    {"file_number": 133, "condition": "OR007@6_3", "fault_type": "outer_race", "fault_diameter_in": "0.007", "severity": "small", "load_hp": 3, "approx_rpm": 1730},
    {"file_number": 169, "condition": "IR014_0", "fault_type": "inner_race", "fault_diameter_in": "0.014", "severity": "medium", "load_hp": 0, "approx_rpm": 1797},
    {"file_number": 170, "condition": "IR014_1", "fault_type": "inner_race", "fault_diameter_in": "0.014", "severity": "medium", "load_hp": 1, "approx_rpm": 1772},
    {"file_number": 171, "condition": "IR014_2", "fault_type": "inner_race", "fault_diameter_in": "0.014", "severity": "medium", "load_hp": 2, "approx_rpm": 1750},
    {"file_number": 172, "condition": "IR014_3", "fault_type": "inner_race", "fault_diameter_in": "0.014", "severity": "medium", "load_hp": 3, "approx_rpm": 1730},
    {"file_number": 185, "condition": "B014_0", "fault_type": "ball", "fault_diameter_in": "0.014", "severity": "medium", "load_hp": 0, "approx_rpm": 1797},
    {"file_number": 186, "condition": "B014_1", "fault_type": "ball", "fault_diameter_in": "0.014", "severity": "medium", "load_hp": 1, "approx_rpm": 1772},
    {"file_number": 187, "condition": "B014_2", "fault_type": "ball", "fault_diameter_in": "0.014", "severity": "medium", "load_hp": 2, "approx_rpm": 1750},
    {"file_number": 188, "condition": "B014_3", "fault_type": "ball", "fault_diameter_in": "0.014", "severity": "medium", "load_hp": 3, "approx_rpm": 1730},
    {"file_number": 197, "condition": "OR014@6_0", "fault_type": "outer_race", "fault_diameter_in": "0.014", "severity": "medium", "load_hp": 0, "approx_rpm": 1797},
    {"file_number": 198, "condition": "OR014@6_1", "fault_type": "outer_race", "fault_diameter_in": "0.014", "severity": "medium", "load_hp": 1, "approx_rpm": 1772},
    {"file_number": 199, "condition": "OR014@6_2", "fault_type": "outer_race", "fault_diameter_in": "0.014", "severity": "medium", "load_hp": 2, "approx_rpm": 1750},
    {"file_number": 200, "condition": "OR014@6_3", "fault_type": "outer_race", "fault_diameter_in": "0.014", "severity": "medium", "load_hp": 3, "approx_rpm": 1730},
    {"file_number": 209, "condition": "IR021_0", "fault_type": "inner_race", "fault_diameter_in": "0.021", "severity": "large", "load_hp": 0, "approx_rpm": 1797},
    {"file_number": 210, "condition": "IR021_1", "fault_type": "inner_race", "fault_diameter_in": "0.021", "severity": "large", "load_hp": 1, "approx_rpm": 1772},
    {"file_number": 211, "condition": "IR021_2", "fault_type": "inner_race", "fault_diameter_in": "0.021", "severity": "large", "load_hp": 2, "approx_rpm": 1750},
    {"file_number": 212, "condition": "IR021_3", "fault_type": "inner_race", "fault_diameter_in": "0.021", "severity": "large", "load_hp": 3, "approx_rpm": 1730},
    {"file_number": 222, "condition": "B021_0", "fault_type": "ball", "fault_diameter_in": "0.021", "severity": "large", "load_hp": 0, "approx_rpm": 1797},
    {"file_number": 223, "condition": "B021_1", "fault_type": "ball", "fault_diameter_in": "0.021", "severity": "large", "load_hp": 1, "approx_rpm": 1772},
    {"file_number": 224, "condition": "B021_2", "fault_type": "ball", "fault_diameter_in": "0.021", "severity": "large", "load_hp": 2, "approx_rpm": 1750},
    {"file_number": 225, "condition": "B021_3", "fault_type": "ball", "fault_diameter_in": "0.021", "severity": "large", "load_hp": 3, "approx_rpm": 1730},
    {"file_number": 234, "condition": "OR021@6_0", "fault_type": "outer_race", "fault_diameter_in": "0.021", "severity": "large", "load_hp": 0, "approx_rpm": 1797},
    {"file_number": 235, "condition": "OR021@6_1", "fault_type": "outer_race", "fault_diameter_in": "0.021", "severity": "large", "load_hp": 1, "approx_rpm": 1772},
    {"file_number": 236, "condition": "OR021@6_2", "outer_race": "outer_race", "fault_type": "outer_race", "fault_diameter_in": "0.021", "severity": "large", "load_hp": 2, "approx_rpm": 1750},
    {"file_number": 237, "condition": "OR021@6_3", "fault_type": "outer_race", "fault_diameter_in": "0.021", "severity": "large", "load_hp": 3, "approx_rpm": 1730},
]


def write_index(dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    index_path = dest_dir / "index.csv"
    fieldnames = ["file_number", "condition", "fault_type", "fault_diameter_in", "severity", "load_hp", "approx_rpm"]
    with open(index_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in INDEX_DATA:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    print(f"Index written to {index_path} ({len(INDEX_DATA)} recordings)")
    return index_path


def download_file(file_num: int, dest_dir: Path) -> Path:
    target = dest_dir / f"{file_num}.mat"
    if target.exists() and target.stat().st_size > 0:
        return target
    url = f"{BASE_URL}/{file_num}.mat"
    print(f"Fetching {url} -> {target.name}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp, open(target, "wb") as out:
        out.write(resp.read())
    return target


def verify_file(mat_path: Path) -> bool:
    if scipy is None:
        return True
    try:
        mat = scipy.io.loadmat(mat_path)
        de_keys = [k for k in mat.keys() if k.endswith("DE_time")]
        if not de_keys:
            print(f"WARNING: No DE_time variable found in {mat_path.name}. Keys: {list(mat.keys())}")
            return False
        return True
    except Exception as e:
        print(f"ERROR reading {mat_path.name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download and verify CWRU 40 benchmark recordings")
    parser.add_argument("--dest", type=str, default="data/cwru", help="Destination folder for CWRU .mat files")
    parser.add_argument("--skip-download", action="store_true", help="Only generate index.csv without downloading")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing .mat files")
    args = parser.parse_args()

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    write_index(dest)

    if args.skip_download:
        return 0

    failed = []
    print(f"\nProcessing {len(INDEX_DATA)} recordings...")
    for item in INDEX_DATA:
        fn = item["file_number"]
        mat_file = dest / f"{fn}.mat"
        if not args.verify_only:
            try:
                download_file(fn, dest)
            except Exception as e:
                print(f"Failed to download {fn}.mat: {e}")
                failed.append((fn, str(e)))
                continue

        if mat_file.exists():
            ok = verify_file(mat_file)
            if not ok:
                failed.append((fn, "missing DE_time or invalid mat"))
        else:
            failed.append((fn, "file missing"))

    if failed:
        print(f"\nCompleted with {len(failed)} failures: {failed}")
        return 1
    else:
        print(f"\nAll {len(INDEX_DATA)} CWRU files verified successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())

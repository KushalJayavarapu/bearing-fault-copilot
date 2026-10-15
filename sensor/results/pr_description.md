## What changed
Follow-up to #4, answering Kushal's question about CWRU terms and runtime data. The model, the results and the contract are unchanged.
- **Data source, terms and citation** (new section in `sensor/README.md`):
  - Source: the CWRU Bearing Data Center.
  - Terms: no dataset license was found on the site (checked 14 Oct 2026). The data is used with attribution and not redistributed: the repo holds only the download script and the SHA-256 manifest, and **Docker images that contain the data must not be pushed to a public registry**.
  - Citation: Smith & Randall, MSSP 64-65:100-131, 2015, doi:10.1016/j.ymssp.2015.04.021 (checked against the DOI on Crossref).
  - Honest limits: lab rig, faults seeded by EDM.
- **Runtime data subset:** with the default demo model:
  - `predict()` and `get_window()` open only the requested recording's `.mat` plus the model file. The healthy baseline for evidence is inside the model file.
  - New: `python -m sensor.build --runtime-only DIR` copies just the 10 held-out 3 hp recordings (34.2 MB, hash-checked) for the final stage of a multi-stage Docker image, instead of all 40 (140.3 MB).
  - The README shows an example stage split. The Dockerfile itself is Karthiik's.
- **Behaviour with partial data:**
  - `list_recordings()` lists only recordings whose file is present: all 40 after a full build, 10 in a runtime image. The fields are unchanged.
  - A missing recording raises a clear `FileNotFoundError`.
- **Tests:** `test_sensor` covers the runtime-only case. `sensor/results/messages.md` has a data and licence reply for Kushal.
- **Handover note:** [`sensor/STATUS.md`](../STATUS.md) is the end-of-day 14 Oct status, linked from the top of `sensor/README.md`. It covers what's done, the measured headline numbers, the caveats, the demo picks, PR history and open items with owners.

## How to test
From the repo root (Git Bash; see `sensor/README.md` for PowerShell):
```bash
python -m venv .venv && source .venv/Scripts/activate
pip install -r sensor/requirements.txt
python -m sensor.build                           # 40 verified files + models (fresh clone: 167 s, mostly download)
python -m sensor.build --runtime-only /tmp/rt    # expect: 10 held-out recordings, 34.2 MB, verified
python -m sensor.test_sensor                     # expect: ... runtime-only data (10 held-out files): ... ok
pip install -r app/api/requirements.txt pytest && python -m pytest -q app/api   # expect: 41 passed
```

## Checklist
- [x] Branch is up to date with `main` (on top of #6)
- [x] Follows the data contract in `docs/contract.md` (not changed)
- [x] No secrets, raw data, source PDFs or model weights committed
- [x] Works in mock mode (`MOCK_MODE=true` or `SENSOR_MOCK=1`); mock still lists all 40 recordings
- [x] Small enough to review in about 10 minutes (7 files, +128 / -51 lines)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

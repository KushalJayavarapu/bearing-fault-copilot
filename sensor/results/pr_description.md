## What changed
Follow-up to #2, from Kushal's review. The model, features and headline numbers are unchanged.
- **Uncertainty bands:** `HIGH_UNCERTAINTY_BELOW = 0.60` and `LOW_UNCERTAINTY_AT_OR_ABOVE = 0.95` plus `uncertainty_level(confidence)` now live in `sensor/config.py`, and no other code hardcodes them. The 0.60 cut-off comes from the task brief. The 0.95 cut-off was chosen by looking at the held-out folds, so accuracy in the medium and low bands is slightly optimistic. The headline model numbers are unaffected.
- **Optional `evidence` field** in the sensor result: envelope-spectrum peaks at BPFI/BPFO/BSF, from the recording's rpm.
  - It is `[]` for healthy windows and weak cases. Weak means `vs_normal < EVIDENCE_MIN_VS_NORMAL = 2.5`, chosen on training loads 0/1/2 only.
  - The healthy baseline is saved in the model file.
  - The mock returns one real outer race (BPFO) entry.
- **`docs/contract.md` section 1 (changed at Kushal's request):**
  - The section 1 sample JSON is unchanged (byte-identical to main). `evidence` is documented below it as a separate "Optional field: evidence" example, with a field table. This keeps `app/api/test_api.py` passing untouched (10 passed).
  - It is marked optional: a missing field means `[]`.
  - It notes that evidence can disagree with `fault_type` and that consumers should show the disagreement. No other part of the contract changed.
- **`python -m sensor.build`:** downloads the 40 recordings and checks each file's size and SHA-256 against `sensor/cwru_manifest.json`. It resumes cut-off transfers, retries a bad hash 3 times, then stops loudly; a mismatched local file also stops the build. Then it trains. A rerun is a 0.2 s no-op. No data or models are committed.

`app/api/uncertainty.py` (#3) has a TODO to import the thresholds from sensor config: it can now use `sensor.config`. I haven't touched `app/`.

**Evidence on the held-out 3 hp windows:**

| fault type | non-empty | precision (strongest peak = true family) | disagrees with classifier |
|---|---|---|---|
| normal | 0.0% | n/a | 0 |
| inner race | 67.2% | 100.0% (238/238) | 0 |
| outer race | 58.8% | 98.1% (204/208) | 4 windows |
| ball | 4.5% | 93.8% (15/16) | 1 window |

OR014@6_3, the uncertain demo pick, returns `[]` in all 118 windows.

**Measured on a laptop:**
- Downloading the 40 files (140.3 MB) takes 281 s; training takes 5.5 s.
- The model files are 1.41 MB and 1.81 MB.
- `predict()` with evidence takes a median 88 ms (p95 108 ms).

**Caveats (unchanged):**
- The 99.0% headline is at an unseen motor load. On bearings the model never saw, accuracy is 40-100%.
- Normal is a single bearing.
- Evidence rarely backs ball faults.
- The data comes from a lab rig with EDM-cut faults.

## How to test
From the repo root (Git Bash; see `sensor/README.md` for PowerShell):
```bash
python -m venv .venv && source .venv/Scripts/activate
pip install -r sensor/requirements.txt
MOCK_MODE=true python -m sensor.predict      # mock with no data or model: contract sample including evidence
python -m sensor.build                       # downloads + verifies 40 files, trains (~5 min first time)
python -m sensor.build                       # rerun: verifies and exits in well under a second
python -m sensor.test_sensor                 # expect: mock ok x2, mock == contract sample, manifest ok, interface ok
python -m sensor.evaluate --evidence         # regenerates sensor/results/evidence.md
pip install -r app/api/requirements.txt pytest && python -m pytest -q app/api/test_api.py   # Kushal's API tests: 10 passed
```

## Checklist
- [x] Branch is up to date with `main`: rebased onto main after #2 was squash-merged (only the new commits were replayed), and again after #3.
- [x] Follows the data contract in `docs/contract.md`: section 1 is updated at Kushal's request, the new field is optional, and nothing else changed.
- [x] No secrets, raw data, source PDFs or model weights committed. Only the SHA-256 manifest (12 KB) describes the data.
- [x] Works in mock mode (`MOCK_MODE=true` or `SENSOR_MOCK=1`); the mock matches the contract sample exactly (checked by `test_sensor`).
- [x] Small enough to review in about 10 minutes: one commit per step.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

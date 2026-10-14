## What changed
Adds the sensor fault classifier under `sensor/`. It takes a CWRU 12 kHz drive-end window and returns the sensor result from `docs/contract.md` section 1. It also provides `list_recordings()`, `get_window(..., max_points=)` and `evidence()`, plus mock mode, the fair-split evaluation and the results in `sensor/results/summary.md`.

**Headline:** 99.0% fault_type accuracy (macro-F1 0.989, severity 97.7%) at a motor load the model never saw, vs 27.7% for always guessing the majority class.

**Caveats:**
- CWRU reuses one physical bearing per fault across loads, and normal is one bearing too. On bearings the model never saw, accuracy is 40-100% depending on fault and size.
- `evidence()` is weak for ball faults.
- The data comes from a lab rig with EDM-cut faults.

Contract: section 1 is unchanged and matches field by field. Two optional additions are proposed to Kushal in chat (an uncertainty.level mapping and an `evidence` field); neither is in the JSON yet.
The 0.60 cut-off comes from the task brief. The 0.95 cut-off was chosen by looking at the held-out folds, so accuracy in the medium and low bands is slightly optimistic. The headline model numbers are unaffected.

Root files are untouched. The only file outside sensor code is the replacement of the `sensor/README.md` placeholder.

## How to test
From the repo root:
```bash
python -m venv .venv && source .venv/Scripts/activate   # PowerShell: .venv\Scripts\Activate.ps1, Linux/macOS: source .venv/bin/activate
pip install -r sensor/requirements.txt
MOCK_MODE=true python -m sensor.predict                 # mock: prints the contract sample, no data or model needed
python -m sensor.data_loading --download                # 56 files, 179 MB -> data/raw/cwru/ (gitignored)
python -m sensor.train                                  # about 5 s, models -> sensor/models/ (gitignored)
python -m sensor.test_sensor                            # expect: "mock ok" x2, then "interface ok" with timings
python -m sensor.evaluate                               # regenerates sensor/results/results.md; numbers should match
```

## Checklist
- [x] Branch is up to date with `main`
- [x] Follows the data contract in `docs/contract.md` (section 1 unchanged; proposed optional additions announced to Kushal, not merged)
- [x] No secrets, raw data, source PDFs or model weights committed (`.mat` and models are gitignored; largest committed file is the 37 KB confusion matrix PNG)
- [x] Works in mock mode (`MOCK_MODE=true` or `SENSOR_MOCK=1`)
- [ ] Small enough to review in about 10 minutes: no. It is the whole sensor folder in one PR, split into small commits by step. Review commit by commit; the interface is in `sensor/predict.py` and the numbers are in `sensor/results/summary.md`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

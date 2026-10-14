# sensor/: CWRU bearing fault classifier

Owner: Harshit. Takes one 2048-sample window (0.17 s) of 12 kHz drive-end vibration and returns the sensor result
from `docs/contract.md` section 1 (fault_type, severity, confidence, probabilities, context).
Runs on CPU; the AMD GPU part of the product is the LLM, not this model.

## Read this before quoting any number

- **99% means "same bearing, new motor load", not "new bearing".** CWRU uses one physical damaged bearing per condition
  across all 4 loads, so leave-one-load-out (LOLO) still tests a bearing the model has seen.
- **On bearings it has never seen, it is much weaker.** Leaving one fault size out gives 1.000 / 0.497 / 0.715 (small / medium / large),
  and outer race at 3 / 12 o'clock gives 0.499 / 0.399. On unseen medium faults, nearly every window is called "ball".
- "normal" is also a single physical bearing, so leave-one-size-out only tests generalisation for the fault classes.
- `evidence()` is weak for ball faults (strongest envelope peak matches BSF in 0-67% of windows) and for OR014@6 (0%).
- No window leakage: every split keeps whole recordings on one side (asserted in code).
- Lab rig with artificial (EDM) faults, not a factory.
- Honest pitch: *"99% at a motor load the model never saw, on the CWRU rig. Generalising to new physical bearings is not solved (40-100% depending on fault and size)."*

Full numbers, splits and reproduce commands: [results/summary.md](results/summary.md).

## Run it (from the repo root)

Tested on Windows 11 with Python 3.13.

```bash
python -m venv .venv
# activate: Git Bash  source .venv/Scripts/activate | PowerShell  .venv\Scripts\Activate.ps1 | Linux/macOS  source .venv/bin/activate
# PowerShell says "running scripts is disabled"? Run  Set-ExecutionPolicy -Scope Process Bypass  first (this window only).
pip install -r sensor/requirements.txt

python -m sensor.data_loading --download   # 56 .mat files (179 MB) -> data/raw/cwru/ (gitignored), then a sanity table of the 40 recordings
python -m sensor.train                     # rebuilds both models -> sensor/models/ (gitignored, 1.4 + 1.8 MB, about 5 s)
python -m sensor.test_sensor               # self-check: mock (both switches), contract shape and types, evidence, timing
python -m sensor.predict "OR007@6_3" 58    # print one sensor result
```

Mock mode needs no data and no model: set `MOCK_MODE=true` (team `.env.example`) or `SENSOR_MOCK=1`.

Data folder: `data/raw/cwru/` in the repo by default. Override with the `SENSOR_DATA_DIR` env var, or `--data-dir PATH` for the downloader.
Files are named `<number>.mat`. The downloader resumes interrupted transfers (the CWRU server cuts each one after about 3 s) and never leaves a partial `.mat` behind.

Results (each writes to `sensor/results/`):

```bash
python -m sensor.evaluate                  # LOLO, hold-out recordings, leave-one-size-out -> results.md, confusion_lolo.png
python -m sensor.evaluate --compare        # feature variants + inner-CV selection -> variants.md (~2 min)
python -m sensor.evaluate --bands          # accuracy per confidence band -> confidence_bands.md
python -m sensor.evaluate --ttd            # time to identify the fault type -> time_to_detect.md
python -m sensor.evaluate --or-positions   # outer race @3/@12 o'clock -> or_positions.md
python -m sensor.demo_picks                # demo recordings and windows -> demo_picks.md
```

## Interface (for Kushal and Karan)

```python
from sensor.predict import predict, list_recordings, get_window, evidence, is_uncertain
predict("OR007@6_3", 58)                    # POST /analyze -> sensor result, exact contract section 1 shape
list_recordings()                           # GET /recordings -> 40 x {recording_id, load_hp, rpm, fault_type, severity, n_windows, held_out}
get_window("OR007@6_3", 58)                 # GET /signal -> {"samples": [2048 floats], "sample_rate_hz": 12000}
get_window("OR007@6_3", 58, max_points=512) # downsampled for the chart: every 4th sample, sample_rate_hz 3000.0
evidence("OR007@6_3", 58)                   # physics facts behind the window (not in the contract yet)
is_uncertain(result)                        # confidence < UNCERTAIN_THRESHOLD (0.6, defined once in predict.py)
```

- **Demo from `held_out=True` recordings** (the 10 recordings at 3 hp, 1730 rpm). The default model (`SENSOR_MODEL=demo`) never trained on them,
  so its confidence is honest. Picks with window ranges are in [results/demo_picks.md](results/demo_picks.md).
  `SENSOR_MODEL=all` uses the model trained on all 40 recordings; on the demo recordings that is in-sample.
- Recording ids: `Normal_0`, `IR007_0`, `B014_2`, `OR021@6_3` ... (condition + `_` + load hp). `window_index` must be in `0 .. n_windows-1`, else `IndexError`.
- `confidence` is the top fault_type probability. Severity is `"none"` whenever fault_type is `normal`. All values are plain str/int/float.
- `list_recordings()` adds `n_windows` and `held_out` to the fields the contract lists for `GET /recordings`.
- `get_window(max_points=...)` keeps every k-th sample. `sample_rate_hz` is the rate of the returned list, so `i / sample_rate_hz` is the true time.
- `evidence()` compares envelope-spectrum peaks at BPFI/BPFO/BSF (x1-3, from the recording's rpm) and kurtosis against the
  99th percentile on healthy windows the model trained on, e.g.
  `{"feature": "envelope_peak", "freq_hz": 105.5, "expected_hz": 103.1, "matches": "BPFO", "harmonic": 1, "vs_normal": 6.14, "strength": "high"}`.
  It returns `[]` for healthy windows.
- **Timing** (laptop CPU, 300 warm calls): `predict` median 84 ms, p95 132 ms; `evidence` median 2.1 ms.

## Scope and method

12 kHz drive-end only. SKF sizes 0.007/0.014/0.021 in (small/medium/large). Outer race @6 o'clock only. 40 recordings = 10 conditions x 4 loads
(5887 windows, 2048 samples, 50% overlap). The 3 and 12 o'clock outer race files are downloaded for the stretch test only and never trained on.
No per-file normalisation. rpm is read from the file (`X###RPM`); 98.mat and 99.mat have none, so they use the table rpm.
99.mat also contains X098 variables; the loader picks the variables matching the file number.

Features (28): RMS, peak, peak-to-peak, crest, kurtosis, skewness; the share of FFT energy within ±5% of BPFI/BPFO/BSF/FTF x1-3; spectral centroid;
envelope-spectrum peak / median ratio at BPFI/BPFO/BSF x1-3 (fixed 2-5 kHz demodulation band, chosen before seeing results).
Models: two RandomForests (300 trees, class_weight=balanced, seed 42, fixed hyperparameters): fault_type (4 classes) and severity (faulty windows only).
Feature set chosen by inner CV on training loads only (see results/summary.md).

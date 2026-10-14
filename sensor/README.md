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
- `evidence` rarely backs ball faults: on held-out windows it is empty for 95.5% of ball windows and for every OR014@6 window.
  When it is non-empty, its strongest peak names the true fault family in 93.8-100% of windows, depending on fault type (results/evidence.md).
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

python -m sensor.build                     # downloads + verifies the 40 recordings, trains the models (see below)
python -m sensor.test_sensor               # self-check: mock (both switches), contract sample, manifest, shape and types, evidence, timing
python -m sensor.predict "OR007@6_3" 58    # print one sensor result
```

Mock mode needs no data and no model: set `MOCK_MODE=true` (team `.env.example`) or `SENSOR_MOCK=1`.

## Data source, terms and citation

- **Source:** Case Western Reserve University Bearing Data Center, https://engineering.case.edu/bearingdatacenter
  (files downloaded from https://engineering.case.edu/bearingdatacenter/download-data-file), accessed October 2026.
- **Terms:** We found no dataset license on the Bearing Data Center site (checked 14 Oct 2026). The data is used here with attribution and is not redistributed: this repo contains only a download script and a SHA-256 manifest, and Docker images that contain the data must not be pushed to a public registry.
- **Citation for proper use of the data:** W. A. Smith and R. B. Randall, "Rolling element bearing diagnostics using the Case Western Reserve University data: A benchmark study," *Mechanical Systems and Signal Processing*, vol. 64–65, pp. 100–131, 2015, doi:10.1016/j.ymssp.2015.04.021 (title, authors, volume and pages checked against the DOI on Crossref).
- **Honest limits:** lab test rig with faults seeded by electro-discharge machining (EDM), not a factory.

## Getting the model and data

`python -m sensor.build` is the one command. It needs no manual steps:
1. Downloads the 40 recordings the model uses into `data/raw/cwru/`, or into `SENSOR_DATA_DIR` if set.
2. Checks every file's size and SHA-256 against the committed `sensor/cwru_manifest.json`, which lists the file number, recording id, bytes, SHA-256 and source URL.
3. Trains the models into `sensor/models/`.

How it handles failures:
- **Cut-off transfers:** the CWRU server cuts every transfer after about 3 s, so the downloader resumes with HTTP Range requests.
- **Bad downloads:** a file is only renamed from `.part` to `.mat` after its hash matches. A wrong hash is retried 3 times, then the build stops with an error.
- **Bad local files:** a file already on disk that doesn't match the manifest (for example a truncated one from an older download) also stops the build. It is never used and never silently deleted.
- **Reruns:** when everything is already in place, a rerun only re-checks the hashes and exits.

Measured on this laptop:
- Downloading the 40 files (140.3 MB) takes 281 s, mostly waiting on the server's cut-offs.
- Training both models takes 5.5 s.
- The model files are 1.41 MB (demo, the default) and 1.81 MB (all).
- A no-op rerun takes 0.2 s.

Data and models are never committed:
- The team rule keeps raw data and weights out of git.
- The CWRU license is still unchecked, so we don't redistribute the data or anything derived from it.
- The build is deterministic (seed 42), so a rebuild gives the same model.

**Dockerfile:** run `python -m sensor.build` at image build time (`RUN python -m sensor.build`). The image then already contains the data and models, so the live demo never downloads anything at startup.

**Runtime data:** with the default demo model:
- `predict()` and `get_window()` open only the requested recording's `.mat` plus `sensor_model_demo.joblib`. The healthy baseline for evidence is inside the model file.
- `list_recordings()` lists only the recordings whose file is present.
- A recording that isn't present raises a clear `FileNotFoundError`.

So a runtime image needs only the demo model (1.41 MB) and the 10 held-out 3 hp recordings (34.2 MB), instead of all 40 (140.3 MB). `python -m sensor.build --runtime-only DIR` copies those 10 files into `DIR`, hash-checked. A multi-stage Dockerfile could look like this (for Karthiik; this is not the project's Dockerfile):

```dockerfile
FROM python:3.13-slim AS builder
WORKDIR /app
COPY sensor/ sensor/
RUN pip install -r sensor/requirements.txt && python -m sensor.build && python -m sensor.build --runtime-only /runtime-data

FROM python:3.13-slim
WORKDIR /app
COPY sensor/ sensor/
RUN pip install -r sensor/requirements.txt
COPY --from=builder /app/sensor/models/sensor_model_demo.joblib sensor/models/
COPY --from=builder /runtime-data/ data/raw/cwru/
# contains CWRU data: never push this image to a public registry
```

Other pieces:
- The stretch-test files (outer race @3/@12 o'clock) come from `python -m sensor.data_loading --download`, which downloads all 56 files with the same checks.
- `python -m sensor.train` forces a retrain.
- `--data-dir PATH` overrides the data folder for the downloader.

Results (each writes to `sensor/results/`):

```bash
python -m sensor.evaluate                  # LOLO, hold-out recordings, leave-one-size-out -> results.md, confusion_lolo.png
python -m sensor.evaluate --compare        # feature variants + inner-CV selection -> variants.md (~2 min)
python -m sensor.evaluate --bands          # accuracy per confidence band -> confidence_bands.md
python -m sensor.evaluate --evidence       # evidence threshold sweep, precision, disagreement -> evidence.md
python -m sensor.evaluate --ttd            # time to identify the fault type -> time_to_detect.md
python -m sensor.evaluate --or-positions   # outer race @3/@12 o'clock -> or_positions.md
python -m sensor.demo_picks                # demo recordings and windows -> demo_picks.md
```

## Interface (for Kushal and Karan)

```python
from sensor.predict import predict, list_recordings, get_window, evidence, is_uncertain
from sensor.config import uncertainty_level
predict("OR007@6_3", 58)                    # POST /analyze -> sensor result, exact contract section 1 shape
list_recordings()                           # GET /recordings -> 40 x {recording_id, load_hp, rpm, fault_type, severity, n_windows, held_out}
get_window("OR007@6_3", 58)                 # GET /signal -> {"samples": [2048 floats], "sample_rate_hz": 12000}
get_window("OR007@6_3", 58, max_points=512) # downsampled for the chart: every 4th sample, sample_rate_hz 3000.0
evidence("OR007@6_3", 58)                   # the same list predict() returns in "evidence"
is_uncertain(result)                        # True when uncertainty level is "high"
uncertainty_level(result["confidence"])     # "low" | "medium" | "high", for the final answer's uncertainty.level
```

- **Demo from `held_out=True` recordings** (the 10 recordings at 3 hp, 1730 rpm). The default model (`SENSOR_MODEL=demo`) never trained on them,
  so its confidence is honest. Picks with window ranges are in [results/demo_picks.md](results/demo_picks.md).
  `SENSOR_MODEL=all` uses the model trained on all 40 recordings; on the demo recordings that is in-sample.
- Recording ids: `Normal_0`, `IR007_0`, `B014_2`, `OR021@6_3` ... (condition + `_` + load hp). `window_index` must be in `0 .. n_windows-1`, else `IndexError`.
- `confidence` is the top fault_type probability. Severity is `"none"` whenever fault_type is `normal`. All values are plain str/int/float.
- `list_recordings()` adds `n_windows` and `held_out` to the fields the contract lists for `GET /recordings`.
- `get_window(max_points=...)` keeps every k-th sample. `sample_rate_hz` is the rate of the returned list, so `i / sample_rate_hz` is the true time.
- **`evidence`** (optional field, defined in `docs/contract.md` section 1; a missing field means `[]`): envelope-spectrum peaks at
  BPFI/BPFO/BSF x1-3, computed from the recording's rpm and compared with the healthy baseline saved in the model file, e.g.
  `{"feature": "envelope_peak", "freq_hz": 105.5, "expected_hz": 103.1, "matches": "BPFO", "harmonic": 1, "vs_normal": 6.14, "strength": "high"}`.
  A peak is only listed if `vs_normal >= EVIDENCE_MIN_VS_NORMAL` (2.5, `sensor/config.py`, chosen on training loads 0/1/2 only).
  So healthy windows and weak cases return `[]`. Evidence is computed independently of the classifier and can disagree with `fault_type`
  (5 of 1534 held-out windows). Show the disagreement to the technician instead of hiding it.
- **Uncertainty bands** (all thresholds live in `sensor/config.py`): high below 0.60, medium 0.60 to 0.95, low at or above 0.95.
  The bands were chosen on held-out data: 0.60 comes from the task brief, and only 0.95 was picked by looking at held-out folds,
  so the band accuracies in results/confidence_bands.md are slightly optimistic.
- **Timing** (laptop CPU, 300 warm calls, evidence included): `predict` median 88 ms, p95 108 ms; first call 120 ms.

## Scope and method

12 kHz drive-end only. SKF sizes 0.007/0.014/0.021 in (small/medium/large). Outer race @6 o'clock only. 40 recordings = 10 conditions x 4 loads
(5887 windows, 2048 samples, 50% overlap). The 3 and 12 o'clock outer race files are downloaded for the stretch test only and never trained on.
No per-file normalisation. rpm is read from the file (`X###RPM`); 98.mat and 99.mat have none, so they use the table rpm.
99.mat also contains X098 variables; the loader picks the variables matching the file number.

Features (28): RMS, peak, peak-to-peak, crest, kurtosis, skewness; the share of FFT energy within ±5% of BPFI/BPFO/BSF/FTF x1-3; spectral centroid;
envelope-spectrum peak / median ratio at BPFI/BPFO/BSF x1-3 (fixed 2-5 kHz demodulation band, chosen before seeing results).
Models: two RandomForests (300 trees, class_weight=balanced, seed 42, fixed hyperparameters): fault_type (4 classes) and severity (faulty windows only).
Feature set chosen by inner CV on training loads only (see results/summary.md).

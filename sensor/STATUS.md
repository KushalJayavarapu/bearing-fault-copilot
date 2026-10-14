# sensor/ status: end of day 14 Oct 2026

Handover note (Harshit). Every number below comes from the committed results files; full detail is in [results/summary.md](results/summary.md).

## Done
- **Classifier:** CWRU 12 kHz drive end, 28 features, two RandomForests (fault_type, severity), seed 42. See [README: Scope and method](README.md#scope-and-method).
- **Fair-split evaluation:** leave-one-load-out, held-out recordings, leave-one-fault-size-out, outer race @3/@12 o'clock. See [results/results.md](results/results.md) and [results/or_positions.md](results/or_positions.md).
- **Demo model:** trained on loads 0/1/2; the 10 recordings at 3 hp are held out (`held_out=True`). See [results/demo_picks.md](results/demo_picks.md).
- **Uncertainty bands:** `uncertainty_level()` and both thresholds live in [config.py](config.py). See [results/confidence_bands.md](results/confidence_bands.md).
- **Optional `evidence` field:** documented in [docs/contract.md section 1](../docs/contract.md). Results in [results/evidence.md](results/evidence.md).
- **`python -m sensor.build`:** downloads the data, checks it against the SHA-256 manifest ([cwru_manifest.json](cwru_manifest.json)) and trains. See [README: Getting the model and data](README.md#getting-the-model-and-data).
- **Runtime-only subset:** `--runtime-only DIR` copies 10 files (34.2 MB) for a slim Docker stage. Same README section.
- **Data terms and citation:** see [README: Data source, terms and citation](README.md#data-source-terms-and-citation).

## Headline numbers (measured)
- **Unseen motor load (leave-one-load-out):** fault_type accuracy 0.990, macro-F1 0.989, severity 0.977. Always guessing the majority class gets 0.277.
- **Unseen bearings:** 40-100% depending on fault and size.
  - Leaving one fault size out: 1.000 / 0.497 / 0.715 (small / medium / large).
  - Outer race @3 / @12 o'clock: 0.499 / 0.399.
- **Demo model on the held-out 3 hp recordings:** accuracy 0.964, mean confidence 0.936, 5.2% of windows below 0.60.
- **Evidence precision on held-out windows:** inner race 100.0% (238/238), outer race 98.1% (204/208), ball 93.8% (15/16). Evidence is empty for every healthy window.
- **Speed:**
  - `predict()` median 88 ms, p95 108 ms.
  - `sensor.build` from nothing: 281 s to download plus 5.5 s to train; a rerun takes 0.2 s.

## Caveats for the pitch
- **Unseen load, not unseen bearing:** CWRU reuses one physical bearing per fault at all 4 loads.
- **Normal is one bearing too:** leave-one-size-out only tests the fault classes.
- **Weak ball evidence:** evidence is empty for 95.5% of ball windows.
- **Lab rig:** the faults were seeded by EDM, not found in a factory.
- **Band cut-offs:** 0.60 comes from the brief; 0.95 was chosen on held-out data, so the band accuracies are slightly optimistic.

## Demo picks (held-out 3 hp)
- **Heroes:** IR021_3 (windows 0-68), OR007@6_3 (0-117), OR021@6_3 (56-71).
- **Uncertain:** OR014@6_3, windows 111-115. Window 114 is called ball at 0.507 (wrong; the true fault is outer race), and evidence is `[]`.

## PR history
- **#2 (merged):** classifier, fair-split evaluation, predict / list_recordings / get_window, mock mode.
- **#4 (merged):** evidence field, uncertainty bands in config, `sensor.build` with the SHA-256 manifest.
- **#8 (open):** data source, terms and citation; runtime-only data subset; this note.

## Open items
- **Kushal:**
  - Review #8.
  - Switch the TODO in `app/api/uncertainty.py` to import from `sensor.config`.
  - Delete the `Co-authored-by` lines when squash-merging.
- **Karthiik:**
  - Build the Docker image on the host, or keep it in a private registry. Never push it to a public registry, because it contains CWRU data.
  - Use the runtime-only stage split.
- **Santos / Karan:** use `evidence` and `uncertainty.level`. When evidence disagrees with `fault_type`, show the disagreement instead of hiding it.
- **Harshit (next):** help Santos build the retrieval query from fault_type, severity and evidence.

## How to run
```bash
python -m venv .venv && source .venv/Scripts/activate   # PowerShell: .venv\Scripts\Activate.ps1
pip install -r sensor/requirements.txt
python -m sensor.build && python -m sensor.test_sensor
SENSOR_MOCK=1 python -m sensor.predict                  # or MOCK_MODE=true: no data, no model
```

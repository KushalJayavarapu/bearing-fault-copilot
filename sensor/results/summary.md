# Sensor model: results summary (source of truth)

CWRU 12 kHz drive-end, SKF fault sizes, outer race @6 o'clock. 40 recordings (10 conditions x 4 loads), 5887 windows of 2048 samples (0.171 s), 50% overlap.
Model: two RandomForests (300 trees, class_weight=balanced, fixed hyperparameters, **seed 42**), 28 features (time domain, FFT band-energy ratios, envelope-spectrum peaks).
Every number below was produced by the commands at the end of this file.

## Headline

**99.0% fault_type accuracy (macro-F1 0.989, severity 97.7%) on a motor load the model never saw** (leave-one-load-out, mean of 4 folds).
Always guessing the most common class gets 27.7%.
**On physical bearings it never saw, accuracy is 40-100% depending on fault and size.** Read the caveats.

## Caveats (say these out loud)

1. **Same bearing across loads.** CWRU uses one damaged bearing per condition at all 4 loads, so leave-one-load-out tests a known bearing at a new load, not a new bearing.
2. **Normal is one bearing too.** Leave-one-size-out therefore only tests generalisation for the fault classes.
3. **Little evidence for ball faults.** `evidence` is empty for 95.5% of held-out ball windows and for every OR014@6 window (section 10). When it is non-empty it is right 93.8-100% of the time.
4. **Lab rig with EDM faults.** The faults were cut on purpose by spark machining on a test rig. This is realistic vibration data, not factory data.
5. **No window leakage.** Every split keeps all windows of a recording on one side (asserted in code). Any tuning used only training loads.

## 1. Leave-one-load-out (headline)

Train on 3 loads, test on the 4th, repeat for each load. Severity accuracy is on truly faulty windows. Baseline = majority class of the training fold.

| test load | windows | fault acc | fault macro-F1 | severity acc | baseline (fault) | baseline (severity) | % conf < 0.6 |
|---|---|---|---|---|---|---|---|
| 0 hp (1797 rpm) | 1295 | 1.000 | 1.000 | 0.926 | 0.183 | 0.335 | 0.6% |
| 1 hp (1772 rpm) | 1529 | 0.999 | 0.999 | 0.988 | 0.308 | 0.333 | 0.4% |
| 2 hp (1750 rpm) | 1529 | 0.997 | 0.996 | 0.994 | 0.309 | 0.334 | 0.4% |
| 3 hp (1730 rpm) | 1534 | 0.964 | 0.962 | 1.000 | 0.308 | 0.334 | 5.2% |
| **mean** | | **0.990** | **0.989** | **0.977** | **0.277** | **0.334** | **1.7%** |

Confusion matrix: [confusion_lolo.png](confusion_lolo.png).
Which features mattered (mean RF importance): peak-to-peak 0.123, RMS 0.115, BPFI envelope peak 0.104, peak 0.098, spectral centroid 0.089, BPFO band energy 0.060.

## 2. Hold out whole recordings (secondary)

4-fold StratifiedGroupKFold by recording (seed 42), one recording per condition per fold, loads mixed.

| fold | windows | fault acc | fault macro-F1 | severity acc |
|---|---|---|---|---|
| 0 | 1531 | 0.997 | 0.997 | 0.992 |
| 1 | 1531 | 1.000 | 1.000 | 0.938 |
| 2 | 1529 | 0.999 | 0.999 | 0.945 |
| 3 | 1296 | 0.951 | 0.956 | 0.990 |
| **mean** | | **0.987** | **0.988** | **0.966** |

Folds: 0 = B007_3, B014_0, B021_2, IR007_1, IR014_1, IR021_2, Normal_3, OR007@6_0, OR014@6_1, OR021@6_0;
1 = B007_0, B014_2, B021_3, IR007_2, IR014_2, IR021_0, Normal_2, OR007@6_2, OR014@6_2, OR021@6_2;
2 = B007_2, B014_3, B021_0, IR007_0, IR014_0, IR021_3, Normal_1, OR007@6_1, OR014@6_0, OR021@6_3;
3 = B007_1, B014_1, B021_1, IR007_3, IR014_3, IR021_1, Normal_0, OR007@6_3, OR014@6_3, OR021@6_1.

## 3. Leave one fault size out (unseen bearings)

All 4 loads of one fault size held out, plus Normal at one load so the normal class is tested. Severity is n/a because the held-out size was never trained on.

| held out | windows | fault acc | fault macro-F1 | baseline (fault) | what goes wrong |
|---|---|---|---|---|---|
| small (0.007) + Normal_0 | 1649 | 1.000 | 1.000 | 0.144 | nothing |
| medium (0.014) + Normal_1 | 1880 | 0.497 | 0.370 | 0.251 | inner race: 468/468 windows called ball; outer race: 459/470 called ball, 11 normal |
| large (0.021) + Normal_2 | 1885 | 0.715 | 0.655 | 0.250 | outer race: 414/472 called inner race; ball: 82/471 called outer race |
| **mean** | | **0.737** | **0.675** | **0.215** | |

## 4. Outer race at 3 and 12 o'clock (unseen bearings)

All-data model (trained on @6 only), fault_type accuracy. All windows of each recording.

| recording | 0 hp | 1 hp | 2 hp | 3 hp |
|---|---|---|---|---|
| OR007@3 | 1.000 | 1.000 | 1.000 | 1.000 |
| OR007@12 | 0.000 | 0.000 | 0.068 | 0.059 |
| OR021@3 | 0.000 | 0.000 | 0.000 | 0.000 |
| OR021@12 | 0.923 | 0.966 | 0.924 | 0.256 |

Pooled: **@3 o'clock 0.499, @12 o'clock 0.399**. Wrong calls are ball or inner race. 0.014 has no 3 or 12 o'clock files at 12 kHz.

## 5. Demo model (honest confidence)

The default model trains on loads 0/1/2. The 10 recordings at 3 hp (1730 rpm) are the demo set (`held_out=True` in `list_recordings()`).
Same 1534 demo windows, two models:

| model | trained on | acc | mean confidence | % confidence = 1.0 | % confidence < 0.6 |
|---|---|---|---|---|---|
| **demo (default)** | loads 0/1/2 | **0.964** | 0.936 | 37.9% | 5.2% |
| all (`SENSOR_MODEL=all`) | all 40 (in-sample here) | 1.000 | 0.993 | 72.6% | 0.0% |

Per-recording stats and the demo picks with window ranges: [demo_picks.md](demo_picks.md).

| demo pick | recording | windows | shows |
|---|---|---|---|
| Hero 1 (inner race) | IR021_3 | 0-68 | inner_race / large, confidence 0.993 (level low), evidence BPFI 158.2 Hz (expected 156.0), vs_normal 3.43 |
| Hero 2 (outer race) | OR007@6_3 | 0-117 | outer_race / small, confidence 0.997 (level low), evidence BPFO 105.5 Hz (expected 103.1), vs_normal 6.14, plus BPFO 2x |
| Hero 3 (outer race) | OR021@6_3 | 56-71 | outer_race / large, confidence 1.0 (level low), evidence BPFO 105.5 Hz (expected 102.8), vs_normal 3.21 |
| Uncertain | OR014@6_3 | 111-115 | window 114: ball / medium, confidence 0.507 (level high, and wrong: true fault is outer race), evidence `[]` |

The heroes are the longest runs that are correct, at uncertainty level low (confidence ≥ 0.95), and backed by evidence naming the true fault family.

## 6. Feature variants (chosen by inner CV only)

| variant | features | LOLO acc | LOLO macro-F1 | LOLO severity | size-out acc small / medium / large | size-out acc mean | size-out macro-F1 mean | inner-CV score (loads 0/1/2) |
|---|---|---|---|---|---|---|---|---|
| baseline (no envelope) | 19 | 0.979 | 0.979 | 0.965 | 0.431 / 0.498 / 0.770 | 0.566 | 0.515 | 0.753 |
| **+envelope (final)** | 28 | **0.990** | **0.989** | **0.977** | 1.000 / 0.497 / 0.715 | 0.737 | 0.675 | **0.836** |
| +envelope -loudness | 25 | 0.989 | 0.988 | 0.956 | 0.996 / 0.517 / 0.721 | 0.745 | 0.685 | 0.835 |

- Inner-CV score = mean of inner leave-one-load-out and inner leave-one-size-out macro-F1, on training loads only. The test folds were never used to choose.
- +envelope beat -loudness by 0.001, which is effectively a tie.
- The trade-off: dropping loudness features gives slightly better unseen-bearing accuracy (+0.008) but worse severity (-0.021).
- Nested LOLO, where each outer fold picks its own variant by inner CV, gives acc 0.990 and macro-F1 0.990.

## 7. Confidence bands (for uncertainty.level)

Bands chosen on held-out data; thresholds and `uncertainty_level()` live in `sensor/config.py`. Out-of-fold predictions only.

| level (proposed) | confidence | LOLO windows | LOLO acc | unseen-bearing windows | unseen-bearing acc |
|---|---|---|---|---|---|
| high | < 0.60 | 100 (1.7%) | 0.590 | 682 (12.6%) | 0.210 |
| medium | 0.60 - 0.95 | 1294 | 0.985 | 3278 | 0.716 |
| low | >= 0.95 | 4493 (76.3%) | 1.000 | 1454 (26.9%) | 0.990 |

The 0.60 cut-off comes from the task brief. The 0.95 cut-off was chosen by looking at the held-out folds, so accuracy in the medium and low bands is slightly optimistic. The headline model numbers are unaffected.

Finer bands: [confidence_bands.md](confidence_bands.md).
A 0.7 cut would make "low" (0.793) less accurate than "medium" (0.835) on unseen bearings, so 0.95 is the cut that keeps the levels in order.

## 8. Time to identify the fault type

The demo model streams consecutive windows of the held-out 3 hp recordings, starting at every 5th window.
A call counts when the majority vote of the windows so far is the true fault type and the mean probability of that class is ≥ 0.6.

| fault type | start points | median | worst | never reached |
|---|---|---|---|---|
| normal | 95 | 0.171 s | 0.171 s | 0 |
| inner race | 72 | 0.171 s | 1.536 s | 0 |
| outer race | 72 | 0.171 s | 0.853 s | 3 (all OR014@6_3) |
| ball | 72 | 0.171 s | 0.171 s | 0 |

In words: **it identifies the fault type from 0.17 s of vibration (median, every class); the worst case is 1.5 s.**
This is time to classify a fault that is already present, not earlier detection of a developing failure.
The 3 misses are on OR014@6_3, where only 69.5% of windows are correct and the ~10 s recording ends before a confident majority.

## 9. Speed

Laptop CPU, 300 warm calls on demo windows:
- `predict()` (evidence included): median 88 ms, p95 108 ms; first call 120 ms.
- `python -m sensor.build` from nothing: downloading the 40 files (140.3 MB) takes 281 s and training both models takes 5.5 s. A rerun with everything present takes 0.2 s.
- Model files: 1.41 MB (demo) and 1.81 MB (all).

## 10. Evidence (optional field)

`evidence` lists the envelope-spectrum peaks at BPFI/BPFO/BSF x1-3 whose `vs_normal` is ≥ 2.5 (`EVIDENCE_MIN_VS_NORMAL`). The definitions are in docs/contract.md section 1; full tables are in [evidence.md](evidence.md).
**The threshold was chosen on training loads 0/1/2 only:** it is the smallest value where, for every condition, at most 5% of windows get a strongest peak from the wrong fault family. The worst case is 3% at 2.5, against 20% at 2.0. It was fixed before looking at the held-out windows below and was not changed after.

Held-out 3 hp windows, demo model:

| fault type | windows | non-empty before (T = 1) | non-empty after (T = 2.5) | precision (strongest peak = true family) | disagrees with classifier |
|---|---|---|---|---|---|
| normal | 473 | 1.7% | 0.0% | n/a | 0 |
| inner race | 354 | 100.0% | 67.2% | 100.0% (238/238) | 0 |
| outer race | 354 | 80.2% | 58.8% | 98.1% (204/208) | 4 windows (1.9% of non-empty) |
| ball | 353 | 90.4% | 4.5% | 93.8% (15/16) | 1 window (6.2% of non-empty) |

- **Empty cases:** IR014_3 drops to 0.9% non-empty, OR014@6_3 and B007_3 to 0%, and B021_3 to 0.8%.
- **OR014@6_3 (the uncertain demo pick):** evidence is `[]` in all 118 windows, including windows 111-115.
- **Disagreement:** evidence is reported as measured even when it disagrees with `fault_type` (5 of 1534 held-out windows). Consumers should show that to the technician.

## Seed, splits, reproduce

- **Seed:** 42 for every model and the StratifiedGroupKFold shuffle.
- **Splits:**
  - leave-one-load-out: 4 folds by load_hp.
  - hold out recordings: StratifiedGroupKFold(4), groups = recording, strata = condition.
  - leave one fault size out: 3 folds; Normal held out at loads 0/1/2 respectively.
  - demo: train on loads 0/1/2, show 3 hp.

```bash
python -m venv .venv
# activate: Git Bash  source .venv/Scripts/activate | PowerShell  .venv\Scripts\Activate.ps1 | Linux/macOS  source .venv/bin/activate
pip install -r sensor/requirements.txt
python -m sensor.build                     # 40 verified files -> data/raw/cwru/, models -> sensor/models/
python -m sensor.data_loading --download   # adds the 16 stretch-test files for section 4
python -m sensor.test_sensor               # self-check
python -m sensor.evaluate                  # sections 1-3 -> results.md, confusion_lolo.png
python -m sensor.evaluate --or-positions   # section 4 -> or_positions.md
python -m sensor.demo_picks                # section 5 -> demo_picks.md
python -m sensor.evaluate --compare        # section 6 -> variants.md
python -m sensor.evaluate --bands          # section 7 -> confidence_bands.md
python -m sensor.evaluate --ttd            # section 8 -> time_to_detect.md
python -m sensor.evaluate --evidence       # section 10 -> evidence.md
```

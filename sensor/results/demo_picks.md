# Demo picks (held-out 3 hp recordings, demo model never trained on them)

Reproduce: `python -m sensor.demo_picks`. Window = 2048 samples (0.171 s); window i starts at i x 1024 samples.

## All held-out recordings (window level, demo model)

| recording | true | windows | acc | mean conf | % conf < 0.6 | evidence non-empty | strongest peak = true family | evidence disagrees with prediction (windows) | predictions |
|---|---|---|---|---|---|---|---|---|---|
| Normal_3 | normal | 473 | 1.000 | 0.998 | 0.0% | 0.0% | n/a | 0 | normal:473 |
| IR007_3 | inner_race | 119 | 1.000 | 0.948 | 0.0% | 100.0% | 100.0% | 0 | inner_race:119 |
| IR014_3 | inner_race | 117 | 0.838 | 0.701 | 28.2% | 0.9% | 0.9% | 0 | ball:19, inner_race:98 |
| IR021_3 | inner_race | 118 | 1.000 | 0.990 | 0.0% | 100.0% | 100.0% | 0 | inner_race:118 |
| B007_3 | ball | 117 | 1.000 | 0.992 | 0.0% | 0.0% | 0.0% | 0 | ball:117 |
| B014_3 | ball | 118 | 1.000 | 0.941 | 0.8% | 12.7% | 12.7% | 0 | ball:118 |
| B021_3 | ball | 118 | 1.000 | 0.971 | 0.0% | 0.8% | 0.0% | 1 | ball:118 |
| OR007@6_3 | outer_race | 118 | 1.000 | 0.994 | 0.0% | 100.0% | 100.0% | 0 | outer_race:118 |
| OR014@6_3 | outer_race | 118 | 0.695 | 0.666 | 38.1% | 0.0% | 0.0% | 0 | ball:36, outer_race:82 |
| OR021@6_3 | outer_race | 118 | 1.000 | 0.969 | 0.8% | 76.3% | 72.9% | 4 | outer_race:118 |

## Demo model vs all-data model on the same 1534 held-out windows

| model | trained on | acc | mean conf | % conf == 1.0 | % conf < 0.6 |
|---|---|---|---|---|---|
| demo | loads 0/1/2 (default) | 0.964 | 0.936 | 37.9% | 5.2% |
| all | all 40 recordings (in-sample here) | 1.000 | 0.993 | 72.6% | 0.0% |

## Hero picks (correct, uncertainty level low: confidence >= 0.95, evidence non-empty with strongest peak = true fault family)

Ranked by the share of windows meeting all three; window range = longest consecutive run.

97.5% of windows qualify; run of 69 windows.
### Hero 1 (inner race): `IR021_3`, windows 0-68 (show window 34)

- prediction: **inner_race / large**, confidence **0.9933**, probabilities {"normal": 0.0, "inner_race": 0.9933, "outer_race": 0.0067, "ball": 0.0}
- evidence: `[{"feature": "envelope_peak", "freq_hz": 158.2, "expected_hz": 156.0, "matches": "BPFI", "harmonic": 1, "vs_normal": 3.43, "strength": "medium"}]`

100.0% of windows qualify; run of 118 windows.
### Hero 2 (outer race): `OR007@6_3`, windows 0-117 (show window 58)

- prediction: **outer_race / small**, confidence **0.9967**, probabilities {"normal": 0.0, "inner_race": 0.0033, "outer_race": 0.9967, "ball": 0.0}
- evidence: `[{"feature": "envelope_peak", "freq_hz": 105.5, "expected_hz": 103.1, "matches": "BPFO", "harmonic": 1, "vs_normal": 6.14, "strength": "high"}, {"feature": "envelope_peak", "freq_hz": 205.1, "expected_hz": 206.1, "matches": "BPFO", "harmonic": 2, "vs_normal": 5.25, "strength": "high"}]`

66.9% of windows qualify; run of 16 windows.
### Hero 3: `OR021@6_3`, windows 56-71 (show window 63)

- prediction: **outer_race / large**, confidence **1.0**, probabilities {"normal": 0.0, "inner_race": 0.0, "outer_race": 1.0, "ball": 0.0}
- evidence: `[{"feature": "envelope_peak", "freq_hz": 105.5, "expected_hz": 102.8, "matches": "BPFO", "harmonic": 1, "vs_normal": 3.21, "strength": "medium"}, {"feature": "envelope_peak", "freq_hz": 205.1, "expected_hz": 205.6, "matches": "BPFO", "harmonic": 2, "vs_normal": 2.59, "strength": "medium"}]`

## Uncertain pick (uncertainty level high: confidence < 0.6, for the human-confirm moment)

Recording with the most uncertain windows: `OR014@6_3`. Uncertain windows: 45 of 118 (38.1%): [9, 10, 11, 15, 16, 25, 32, 33, 41, 42, 45, 46, 51, 53, 57, 58, 59, 61, 62, 66, 67, 68, 69, 70, 73, 76, 80, 84, 85, 88, 89, 90, 91, 92, 94, 96, 97, 98, 102, 109, 111, 112, 113, 114, 115].
Among uncertain windows, correct: 53.3%; window-level acc overall 0.695, mean conf 0.666.

### Uncertain (longest run of 5 consecutive windows below 0.6): `OR014@6_3`, windows 111-115 (show window 114)

- prediction: **ball / medium**, confidence **0.5067**, probabilities {"normal": 0.01, "inner_race": 0.0, "outer_race": 0.4833, "ball": 0.5067}
- evidence: `[]`


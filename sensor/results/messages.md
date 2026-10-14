# Messages (copy the text inside each block)

## To Kushal: contract proposal

```text
Hi Kushal, sensor is ready on Harshit-Branch. Section 1 of docs/contract.md matches my output field by field (mock returns the exact sample). Two proposals, nothing breaks if you say no:

1) uncertainty.level from sensor confidence, no new field. Measured on predictions the model never trained on:
- high: confidence < 0.60 (accuracy 59% at a seen-bearing new load, 21% on unseen bearings)
- medium: 0.60 to 0.95 (98.5% / 72%)
- low: >= 0.95 (100% / 99%)
The 0.95 cut is the one that keeps the levels in order on unseen bearings; with 0.7, "low" would be less accurate than "medium". Full table: sensor/results/confidence_bands.md

2) Optional "evidence" list in the sensor result, e.g. {"feature": "envelope_peak", "freq_hz": 105.5, "expected_hz": 103.1, "matches": "BPFO", "harmonic": 1, "vs_normal": 6.14, "strength": "high"}. It is the measured fault-frequency peak behind the call, so Santos's query and the LLM explanation can cite physics, not just a label. It finds the right peak in 97-100% of inner race windows and of outer race 0.007/0.021 windows, and it is empty for healthy windows. It is weak or empty for ball faults and outer race 0.014, so the explanation must not over-claim there. Already built as evidence(recording_id, window_index); I add it to the JSON and mock only if you agree.

For meta.latency_ms.classifier: predict() median 84 ms, p95 132 ms on a laptop CPU (first call ~250 ms while it loads the model). The classifier runs on CPU; the AMD part stays the LLM.
```

## Team chat summary

```text
Sensor update (Harshit): fault classifier is frozen and on Harshit-Branch, PR coming.
Headline: 99.0% fault-type accuracy (macro-F1 0.989, severity 97.7%) at a motor load the model never saw. Always guessing the most common class gets 27.7%.
Caveat for the pitch: CWRU reuses one bearing per fault, so on bearings it never saw accuracy is 40-100% depending on fault and size. Ball-fault evidence is weak. Lab rig, EDM faults.
For the pitch: it identifies the fault type from 0.17 s of vibration (median), worst case 1.5 s. Prediction takes about 84 ms.
Demo: use the held_out recordings (3 hp). Picks with window ranges are in sensor/results/demo_picks.md: IR007_3 and OR007@6_3 are hero cases, and OR014@6_3 windows 111-115 trigger the uncertainty warning for the human-confirm moment.
Mock: MOCK_MODE=true or SENSOR_MOCK=1, no data or model needed. All numbers: sensor/results/summary.md.
```

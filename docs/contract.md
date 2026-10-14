# Data contract (draft v0.1)

The agreed shape of the data passed between our parts. Kushal owns this file. A change is announced in the team chat before it is merged. Every part also offers a mock mode that returns the samples below, so nobody is blocked.

## Endpoints

| Endpoint | What it does | Returns |
| --- | --- | --- |
| `GET /health` | Checks that every part is up | Status per part |
| `GET /recordings` | Lists the demo recordings | Recording ids, load, rpm, and the true label for demo use |
| `GET /signal` | Gives one window of vibration data for the chart | Sample rate and a downsampled list of samples |
| `POST /analyze` | Body: recording id and window index | The final answer below |
| `POST /confirm` | Body: request id and the human's decision (`confirmed` or `escalated`) | Stored confirmation |

## 1. Sensor result (classifier to orchestrator)

```json
{
  "recording_id": "OR007@6_0",
  "window_index": 12,
  "fault_type": "outer_race",
  "severity": "small",
  "confidence": 0.93,
  "probabilities": {"normal": 0.01, "inner_race": 0.02, "outer_race": 0.93, "ball": 0.04},
  "context": {"sensor": "drive_end", "sample_rate_hz": 12000, "load_hp": 0, "rpm": 1797}
}
```

`fault_type` is one of `normal`, `inner_race`, `outer_race`, `ball`. `severity` is one of `none`, `small` (0.007 in), `medium` (0.014 in), `large` (0.021 in).

### Optional field: evidence

The sensor result may also carry `evidence`, for example for the sample above:

```json
{"evidence": [{"feature": "envelope_peak", "freq_hz": 105.5, "expected_hz": 107.3, "matches": "BPFO", "harmonic": 1, "vs_normal": 5.93, "strength": "high"}]}
```

`evidence` is **optional**. Consumers must treat a missing `evidence` field exactly like `[]`. It lists the measured fault-frequency peaks behind the window, strongest first. It is `[]` for healthy windows and for weak cases (no peak clears the threshold). It is computed from the signal, independently of the classifier, so it **can disagree with `fault_type`**. When it does, consumers should show the disagreement to the technician, not hide it. Each entry:

| Field | Meaning |
| --- | --- |
| `feature` | Always `envelope_peak` in v0.1: a peak in the envelope spectrum (2-5 kHz band-pass, Hilbert envelope, FFT of the 2048-sample window). |
| `freq_hz` | Frequency of the highest envelope-spectrum bin within ±5% of `expected_hz` (bins are 5.86 Hz wide). |
| `expected_hz` | Fault frequency from the recording's rpm: multiplier x `harmonic` x rpm / 60. Drive-end multipliers: BPFI 5.4152, BPFO 3.5848, BSF 4.7135, FTF 0.39828. |
| `matches` | `BPFI` (inner race), `BPFO` (outer race), `BSF` (ball) or `FTF` (cage). v0.1 emits BPFI, BPFO and BSF only. |
| `harmonic` | 1 = fundamental, 2 = 2x, 3 = 3x. A 2x or 3x entry is only listed if the same family's 1x entry also clears the threshold. |
| `vs_normal` | How far the peak stands out from a healthy bearing. ratio = (envelope-spectrum amplitude at `freq_hz`) / (median envelope-spectrum amplitude over 0-1000 Hz in the same window); `vs_normal` = ratio / (99th percentile of that same ratio, for the same fault frequency and harmonic, over all healthy windows at the loads the model was trained on). |
| `strength` | `medium` for 2.5 <= `vs_normal` < 5.0, `high` for `vs_normal` >= 5.0. Peaks below 2.5 count as `low` and are dropped, so `low` is never emitted. |

## 2. Retrieval (orchestrator to retrieval and back)

Request:

```json
{"query": "outer race defect, small, deep groove ball bearing: causes and actions", "fault_type": "outer_race", "severity": "small", "top_k": 5}
```

Response:

```json
{"passages": [{"chunk_id": "skf-damage-p34-c2", "text": "...", "source_title": "Bearing damage and failure analysis", "source_type": "guide", "page": 34, "url": "https://..."}]}
```

`source_type` is `guide`, `playbook` or `log`. Synthetic log entries are always marked as synthetic.

## 3. Final answer (orchestrator to screen)

```json
{
  "request_id": "req-0001",
  "sensor": { },
  "explanation": "Plain-language summary of what is wrong.",
  "likely_causes": ["..."],
  "recommended_actions": [
    {"step": "...", "safety_critical": true, "citation_ids": ["skf-damage-p34-c2"]}
  ],
  "needs_human_confirm": true,
  "citations": [
    {"id": "skf-damage-p34-c2", "source_title": "...", "page": 34, "url": "https://...", "excerpt": "short snippet"}
  ],
  "uncertainty": {"level": "low", "note": "..."},
  "meta": {"model": "...", "served_on": "AMD ...", "latency_ms": {"classifier": 0, "retrieval": 0, "llm": 0, "total": 0}}
}
```

`sensor` repeats the sensor result from step 1. `uncertainty.level` is `low`, `medium` or `high`. Citation ids come only from retrieved chunks, never from the model's imagination.

## Rules

- Field names are lowercase with underscores, exactly as above.
- The data set for v0.1 is the 12 kHz drive end recordings with the SKF fault sizes (0.007, 0.014, 0.021 inch) plus normal, at all four loads.
- A change to this contract is announced in the team chat before it is merged.

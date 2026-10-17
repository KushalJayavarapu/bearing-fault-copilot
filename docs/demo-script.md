# Demo script (about 3 minutes)

Record in **real mode** (`MOCK_MODE=false`, `LLM_MOCK=false`, phone hotspot if the Wi-Fi blocks the LLM). Before recording: `GET /health` shows `llm: live`, and re-run `python -m app.api.llm_compare` the same morning in case the model was withdrawn. Do one practice take; the LLM takes 7 to 15 s per analysis, so cut or talk over the spinner.

| Time | Show | Say |
| --- | --- | --- |
| 0:00 | Title / header, "LIVE" badge | "Factory bearings fail. We built a copilot that detects the fault, explains it, and tells a technician what to do, with a person confirming anything risky." |
| 0:20 | Pick `IR021_3` (held-out 3 hp), window 12 | "This recording was never used for training. The classifier reads one slice of vibration." |
| 0:35 | Signal and spectrum charts, evidence panel | "It calls an inner-race fault and shows why: a peak at the inner-race fault frequency, well above the healthy baseline." |
| 0:55 | Click Analyze, wait | "Retrieval pulls the relevant maintenance notes, and an LLM served on AMD GPUs through Token Factory writes the explanation." |
| 1:15 | Answer: explanation, causes, actions, citations | "Every action points to the passage it came from. The sensor result and the citations are filled in by code, not by the model, so the model cannot invent them." |
| 1:40 | Safety-critical step and the confirm gate | "Stopping or opening the machine is flagged. Nothing is accepted until a person confirms or escalates." Click Confirm. |
| 2:00 | Switch to `OR014@6_3`, window 114 | "Now a hard case. The classifier is unsure here (called ball at 0.51; the real fault is outer race)." |
| 2:20 | Analyze; point at uncertainty and the first action | "It says so, calls the fault a possibility, and puts manual inspection first. It does not bluff." |
| 2:40 | `/health` or README "What the classifier can and cannot do" | "Honest limits: 99% is for an unseen motor load, not an unseen bearing. Lab data, not a factory." |
| 2:55 | Close | "Detect, explain, act, with a human in the loop. Code and instructions are in the repo." |

If the LLM fails mid-recording, the app shows a degraded answer (sensor, uncertainty, citations, plain "explanation unavailable"). Retake rather than explain it away, or use it deliberately as the "it fails safe" moment.

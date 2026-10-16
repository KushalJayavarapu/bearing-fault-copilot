"""Scenario fixtures from the real sensor on the held-out 3 hp windows: python -m rag.eval.make_fixtures

Writes rag/eval/fixtures/scenarios.json: sensor.predict() output only (no raw signal), each tagged:
  sweep      6 evenly spaced windows of every held-out recording (each fault type x severity, normal)
  hero       the hero picks from sensor/results/demo_picks.md (middle of the stated window run)
  uncertain  OR014@6_3 windows 111-115 (window 114 is called ball at 0.507, evidence [])
  conflict   every held-out window where the strongest vibration peak disagrees with the classifier,
             exactly as app.api.orchestrator.evidence_conflict defines it
Needs the CWRU data and the demo model (python -m sensor.build).
"""
import json
from pathlib import Path

import numpy as np

from app.api.orchestrator import evidence_conflict
from sensor.data_loading import RECORDINGS
from sensor.predict import list_recordings, predict

OUT = Path(__file__).parent / "fixtures" / "scenarios.json"
HEROES = [("IR021_3", 34), ("OR007@6_3", 58), ("OR021@6_3", 63)]
UNCERTAIN = [("OR014@6_3", i) for i in range(111, 116)]
SWEEP_PER_RECORDING = 6


def main():
    held = [r for r in list_recordings() if r["held_out"]]
    chosen = {}  # (recording, window) -> set of tags

    def add(rid, i, tag):
        chosen.setdefault((rid, int(i)), set()).add(tag)

    for r in held:
        for i in np.linspace(0, r["n_windows"] - 1, SWEEP_PER_RECORDING).round().astype(int):
            add(r["recording_id"], i, "sweep")
        for i in range(r["n_windows"]):  # scan every window for evidence/classifier disagreement
            if evidence_conflict(predict(r["recording_id"], i)):
                add(r["recording_id"], i, "conflict")
    for rid, i in HEROES:
        add(rid, i, "hero")
    for rid, i in UNCERTAIN:
        add(rid, i, "uncertain")

    scenarios = []
    for (rid, i), tags in sorted(chosen.items()):
        s = predict(rid, i)
        scenarios.append({"id": f"{rid}#{i}", "tags": sorted(tags), "true_fault": RECORDINGS[rid]["fault_type"],
                          "true_severity": RECORDINGS[rid]["severity"], "sensor": s})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(scenarios, indent=1) + "\n", encoding="utf-8", newline="\n")
    counts = {t: sum(t in s["tags"] for s in scenarios) for t in ("sweep", "hero", "uncertain", "conflict")}
    print(f"{len(scenarios)} scenarios -> {OUT}  {counts}")


if __name__ == "__main__":
    main()

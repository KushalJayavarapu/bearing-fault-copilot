"""Demo picks from the held-out 3 hp recordings: python -m sensor.demo_picks -> results/demo_picks.md

Uses the default demo model (never trained on 3 hp). Also reports demo-vs-all model and evidence() match rates.
"""
import json

import joblib
import numpy as np

from .data_loading import RECORDINGS, load_recording, windows
from .evaluate import RESULTS
from .features import extract
from .config import HIGH_UNCERTAINTY_BELOW as HIGH, LOW_UNCERTAINTY_AT_OR_ABOVE as LOW
from .predict import evidence, list_recordings, predict
from .train import MODEL_PATHS

FAMILY = {"inner_race": "BPFI", "outer_race": "BPFO", "ball": "BSF"}


def window_table(models, rid):
    sig, rpm = load_recording(rid)
    X = extract(windows(sig), rpm)
    out = {}
    for v, m in models.items():
        p = m["fault_type"].predict_proba(X[:, m["cols"]])
        out[v] = (m["fault_type"].classes_[p.argmax(1)], p.max(1))
    return out


def longest_run(mask):
    best, start = (0, 0), None
    for i, ok in enumerate(list(mask) + [False]):
        if ok and start is None:
            start = i
        elif not ok and start is not None:
            best = max(best, (i - start, start))
            start = None
    return best[1], best[1] + best[0] - 1, best[0]


def top_env(ev):
    env = [e for e in ev if e["feature"] == "envelope_peak"]
    return env[0] if env else None


if __name__ == "__main__":
    models = {v: joblib.load(p) for v, p in MODEL_PATHS.items()}
    held = [r for r in list_recordings() if r["held_out"]]
    rows, comp, hero_cands = [], {v: [] for v in models}, []
    for r in held:
        rid, true = r["recording_id"], r["fault_type"]
        wt = window_table(models, rid)
        for v, (pred, conf) in wt.items():
            comp[v].append((pred == true, conf))
        pred, conf = wt["demo"]
        evs = [evidence(rid, i) for i in range(r["n_windows"])]
        tops = [top_env(e) for e in evs]
        env_match = np.array([t is not None and t["matches"] == FAMILY.get(true) for t in tops])
        disagree = sum(t is not None and t["matches"] != FAMILY.get(str(p)) for t, p in zip(tops, pred))
        good = (pred == true) & (conf >= LOW) & env_match
        rows.append((rid, true, r["n_windows"], np.mean(pred == true), conf.mean(), np.mean(conf < HIGH),
                     np.mean([t is not None for t in tops]), np.mean(env_match) if true in FAMILY else float("nan"), disagree,
                     ", ".join(f"{c}:{n}" for c, n in zip(*np.unique(pred, return_counts=True)))))
        if true in ("inner_race", "outer_race"):
            hero_cands.append((good.mean(), rid, longest_run(good)))

    lines = ["# Demo picks (held-out 3 hp recordings, demo model never trained on them)", "",
             "Reproduce: `python -m sensor.demo_picks`. Window = 2048 samples (0.171 s); window i starts at i x 1024 samples.", "",
             "## All held-out recordings (window level, demo model)", "",
             f"| recording | true | windows | acc | mean conf | % conf < {HIGH:g} | evidence non-empty | strongest peak = true family | evidence disagrees with prediction (windows) | predictions |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d:.3f} | {e:.3f} | {f:.1%} | {ne:.1%} | {'n/a' if np.isnan(g) else f'{g:.1%}'} | {dis} | {h} |"
              for a, b, c, d, e, f, ne, g, dis, h in rows]

    lines += ["", "## Demo model vs all-data model on the same 1534 held-out windows", "",
              f"| model | trained on | acc | mean conf | % conf == 1.0 | % conf < {HIGH:g} |", "|---|---|---|---|---|---|"]
    for v, trained in [("demo", "loads 0/1/2 (default)"), ("all", "all 40 recordings (in-sample here)")]:
        ok = np.concatenate([a for a, _ in comp[v]]); c = np.concatenate([b for _, b in comp[v]])
        lines.append(f"| {v} | {trained} | {ok.mean():.3f} | {c.mean():.3f} | {np.mean(c == 1.0):.1%} | {np.mean(c < HIGH):.1%} |")

    def pick_block(title, rid, lo, hi, show):
        p = predict(rid, show)
        ev = evidence(rid, show)
        return [f"### {title}: `{rid}`, windows {lo}-{hi} (show window {show})", "",
                f"- prediction: **{p['fault_type']} / {p['severity']}**, confidence **{p['confidence']}**, probabilities {json.dumps(p['probabilities'])}",
                f"- evidence: `{json.dumps(ev[:2])}`", ""]

    lines += ["", f"## Hero picks (correct, uncertainty level low: confidence >= {LOW:g}, evidence non-empty with strongest peak = true fault family)", "",
              "Ranked by the share of windows meeting all three; window range = longest consecutive run.", ""]
    hero_cands.sort(reverse=True)
    best_ir = next(h for h in hero_cands if h[1].startswith("IR"))
    best_or = next(h for h in hero_cands if h[1].startswith("OR"))
    third = next(h for h in hero_cands if h not in (best_ir, best_or))
    for label, (share, rid, (lo, hi, n)) in [("Hero 1 (inner race)", best_ir), ("Hero 2 (outer race)", best_or), ("Hero 3", third)]:
        lines += [f"{share:.1%} of windows qualify; run of {n} windows."] + pick_block(label, rid, lo, hi, (lo + hi) // 2)

    rid = max(rows, key=lambda r: r[5])[0]
    pred, conf = window_table({"demo": models["demo"]}, rid)["demo"]
    unc = np.flatnonzero(conf < HIGH)
    lo, hi, n = longest_run(conf < HIGH)
    lines += [f"## Uncertain pick (uncertainty level high: confidence < {HIGH:g}, for the human-confirm moment)", "",
              f"Recording with the most uncertain windows: `{rid}`. Uncertain windows: {len(unc)} of {len(conf)} ({len(unc) / len(conf):.1%}): {unc.tolist()}.",
              f"Among uncertain windows, correct: {np.mean(pred[unc] == RECORDINGS[rid]['fault_type']):.1%}; "
              f"window-level acc overall {np.mean(pred == RECORDINGS[rid]['fault_type']):.3f}, mean conf {conf.mean():.3f}.", ""]
    show = lo + int(np.argmin(conf[lo:hi + 1]))
    lines += pick_block(f"Uncertain (longest run of {n} consecutive windows below {HIGH:g})", rid, lo, hi, show)

    (RESULTS / "demo_picks.md").write_text("\n".join(lines) + "\n", newline="\n")
    print("\n".join(lines))

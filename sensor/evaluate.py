"""Honest evaluation: python -m sensor.evaluate

Headline: leave-one-load-out (train 3 loads, test the 4th, x4).
Secondary: hold out whole recordings (4-fold StratifiedGroupKFold by recording, loads mixed).
Stress: leave one fault size out (bearings never seen in training).
Windows of one recording are never split across train and test.

python -m sensor.evaluate            report for FINAL_VARIANT -> results/results.md + confusion_lolo.png
python -m sensor.evaluate --compare  all feature variants side by side + inner-CV selection -> results/variants.md
python -m sensor.evaluate --bands     accuracy per confidence band (for uncertainty.level) -> results/confidence_bands.md
python -m sensor.evaluate --or-positions  outer race @3/@12 o'clock (unseen bearings) -> results/or_positions.md
python -m sensor.evaluate --ttd      time-to-detect on the held-out demo recordings -> results/time_to_detect.md
"""
import sys
from pathlib import Path

import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold

from .data_loading import RECORDINGS
from .features import VARIANTS
from .predict import FAULT_TYPES, UNCERTAIN_THRESHOLD
from .train import FINAL_VARIANT, SEED, build_dataset, fit

warnings.filterwarnings("ignore", "Mean of empty slice")  # all-NaN severity column in size-out table
RESULTS = Path(__file__).resolve().parent / "results"


def _majority(labels):
    """Most common label; ties go to the alphabetically first (set order varies per process)."""
    values, counts = np.unique(labels, return_counts=True)
    return values[counts.argmax()]


def run_fold(X, y_type, y_sev, rec, train, test, variant=FINAL_VARIANT):
    assert not set(rec[train]) & set(rec[test]), "recording leaked across train/test"
    m = fit(X[train], y_type[train], y_sev[train], variant)
    Xt = X[test][:, m["cols"]]
    proba = m["fault_type"].predict_proba(Xt)
    pred = m["fault_type"].classes_[proba.argmax(1)]
    conf = proba.max(1)
    faulty = y_type[test] != "normal"
    sev_pred = m["severity"].predict(Xt[faulty])
    majority = _majority(y_type[train])
    sev_majority = _majority(y_sev[train][y_type[train] != "normal"])
    ok = pred == y_type[test]
    return {
        "acc": accuracy_score(y_type[test], pred),
        "f1": f1_score(y_type[test], pred, average="macro"),
        "sev_acc": accuracy_score(y_sev[test][faulty], sev_pred),
        "base_acc": np.mean(y_type[test] == majority),
        "sev_base_acc": np.mean(y_sev[test][faulty] == sev_majority),
        "uncertain": np.mean(conf < UNCERTAIN_THRESHOLD),
        "acc_confident": ok[conf >= UNCERTAIN_THRESHOLD].mean(),
        "acc_uncertain": ok[conf < UNCERTAIN_THRESHOLD].mean() if (conf < UNCERTAIN_THRESHOLD).any() else float("nan"),
        "n_test": len(test),
        "conf": conf,
        "pred": pred,
        "true": y_type[test],
        "importances": m["fault_type"].feature_importances_,
    }


COLS = ["acc", "f1", "sev_acc", "base_acc", "sev_base_acc", "uncertain", "acc_confident", "acc_uncertain"]
HEAD = "| fold | n_test | fault acc | fault macro-F1 | severity acc | majority baseline (fault) | majority baseline (severity) | % uncertain (<0.6) | acc when confident | acc when uncertain |"


def lolo_splits(load, idx):
    return [(f"test {hp} hp", idx[load[idx] != hp], idx[load[idx] == hp]) for hp in np.unique(load[idx])]


def size_out_splits(y_type, y_sev, load, idx):
    """Hold out one fault size (all its loads) + Normal at one load, so the normal class is in every test fold."""
    loads = np.unique(load[idx])
    out = []
    for i, sev in enumerate(["small", "medium", "large"]):
        te = (y_sev[idx] == sev) | ((y_type[idx] == "normal") & (load[idx] == loads[i]))
        out.append((f"test size {sev} + Normal_{loads[i]}", idx[~te], idx[te]))
    return out


def inner_score(X, y_type, y_sev, rec, load, idx, variant):
    """Selection criterion (fixed before any results): mean of inner-LOLO and inner-size-out fault_type macro-F1,
    computed on idx (training data) only."""
    def f1s(splits):
        return np.mean([run_fold(X, y_type, y_sev, rec, tr, te, variant)["f1"] for _, tr, te in splits])
    return (f1s(lolo_splits(load, idx)) + f1s(size_out_splits(y_type, y_sev, load, idx))) / 2


def table(title, rows):
    lines = [f"### {title}", "", HEAD, "|" + "---|" * 10]
    for name, r in rows:
        lines.append(f"| {name} | {r['n_test']} | " + " | ".join(f"{r[c]:.3f}" for c in COLS) + " |")
    lines.append("| **mean** | | " + " | ".join(f"**{np.nanmean([r[c] for _, r in rows]):.3f}**" for c in COLS) + " |")
    return "\n".join(lines)


def confidence_bands(X, y_type, y_sev, rec, load, cuts=(0.6, 0.7, 0.8, 0.9, 0.95)):
    """Accuracy per confidence band, from out-of-fold predictions only (no window scored by a model that trained on it).
    Used to map sensor confidence to the final answer's uncertainty.level."""
    idx = np.arange(len(X))
    lines = ["### Accuracy by confidence band (out-of-fold fault_type predictions)", "",
             "| split | band | windows | share | accuracy |", "|---|---|---|---|---|"]
    for name, splits in [("leave-one-load-out", lolo_splits(load, idx)),
                         ("leave-one-size-out (unseen bearings)", size_out_splits(y_type, y_sev, load, idx))]:
        rs = [run_fold(X, y_type, y_sev, rec, tr, te) for _, tr, te in splits]
        ok = np.concatenate([r["pred"] == r["true"] for r in rs])
        conf = np.concatenate([r["conf"] for r in rs])
        edges = [0, *cuts, 1.0001]
        for lo, hi in zip(edges, edges[1:]):
            m = (conf >= lo) & (conf < hi)
            label = f"[{lo:.2f}, {min(hi, 1):.2f}{']' if hi > 1 else ')'}"
            lines.append(f"| {name} | {label} | {m.sum()} | {m.mean():.1%} | {ok[m].mean():.3f} |" if m.any() else f"| {name} | {label} | 0 | 0.0% | - |")
    md = "\n".join(lines)
    (RESULTS / "confidence_bands.md").write_text(md + "\n", newline="\n")
    print(md)


def or_positions():
    """All-data model (trained on @6 only) on outer race faults at 3 and 12 o'clock: bearings it never saw."""
    import joblib
    from .data_loading import OR_STRETCH, load_recording, windows
    from .features import extract
    from .train import MODEL_PATHS
    m = joblib.load(MODEL_PATHS["all"])
    lines = ["### Outer race at 3 and 12 o'clock (unseen bearings, all-data model trained on @6 only): fault_type accuracy", "",
             "| recording | file | windows | fault_type acc | most common wrong prediction |", "|---|---|---|---|---|"]
    by_pos = {}
    for rid, meta in OR_STRETCH.items():
        sig, rpm = load_recording(rid)
        pred = m["fault_type"].predict(extract(windows(sig), rpm)[:, m["cols"]])
        wrong = pred[pred != "outer_race"]
        common = max(set(wrong), key=list(wrong).count) if len(wrong) else "-"
        by_pos.setdefault(meta["condition"].split("@")[1], []).append(pred == "outer_race")
        lines.append(f"| {rid} | {meta['file']} | {len(pred)} | {np.mean(pred == 'outer_race'):.3f} | {common} |")
    lines += ["", *(f"- @{p} o'clock, all windows pooled: {np.mean(np.concatenate(v)):.3f}" for p, v in by_pos.items())]
    md = "\n".join(lines)
    (RESULTS / "or_positions.md").write_text(md + "\n", newline="\n")
    print(md)


def time_to_detect(start_every=5):
    """Stream consecutive windows of each held-out demo recording (demo model, never trained on load 3) from many
    start points. Detected = majority vote of window predictions is the true fault_type AND the mean probability of
    that class over the windows so far >= UNCERTAIN_THRESHOLD. Time = seconds of signal consumed."""
    import joblib
    from .data_loading import SAMPLE_RATE_HZ, WINDOW, OVERLAP, load_recording, windows
    from .features import extract
    from .train import DEMO_TEST_LOAD, MODEL_PATHS
    m = joblib.load(MODEL_PATHS["demo"])
    step_s, win_s = WINDOW * (1 - OVERLAP) / SAMPLE_RATE_HZ, WINDOW / SAMPLE_RATE_HZ
    times = {}
    for rid, meta in RECORDINGS.items():
        if meta["load_hp"] != DEMO_TEST_LOAD:
            continue
        sig, rpm = load_recording(rid)
        proba = m["fault_type"].predict_proba(extract(windows(sig), rpm)[:, m["cols"]])
        classes = list(m["fault_type"].classes_)
        true = classes.index(meta["fault_type"])
        votes = proba.argmax(1)
        for s0 in range(0, len(proba), start_every):
            t = None
            for k in range(1, len(proba) - s0 + 1):
                v = np.bincount(votes[s0:s0 + k], minlength=len(classes))
                if v.argmax() == true and v[true] > k / 2 and proba[s0:s0 + k, true].mean() >= UNCERTAIN_THRESHOLD:
                    t = (k - 1) * step_s + win_s
                    break
            times.setdefault(meta["fault_type"], []).append((rid, t))
    lines = ["### Time to a confident correct call (demo model, held-out 3 hp recordings)", "",
             " ".join(time_to_detect.__doc__.split()), "",
             f"Start points: every {start_every}th window. Windows: 2048 samples (0.171 s), 50% overlap (+0.085 s per extra window).", "",
             "| fault_type | recordings | start points | median s | worst s | starts never reaching a call |", "|---|---|---|---|---|---|"]
    for ft in FAULT_TYPES:
        ts = [t for _, t in times[ft] if t is not None]
        miss = [r for r, t in times[ft] if t is None]
        missed = f"{len(miss)} ({', '.join(sorted(set(miss)))})" if miss else "0"
        lines.append(f"| {ft} | {', '.join(sorted({r for r, _ in times[ft]}))} | {len(times[ft])} | "
                     f"{np.median(ts):.3f} | {max(ts):.3f} | {missed} |")
    RESULTS.mkdir(exist_ok=True)
    md = "\n".join(lines)
    (RESULTS / "time_to_detect.md").write_text(md + "\n", newline="\n")
    print(md)


if __name__ == "__main__":
    X, y_type, y_sev, rec, load = build_dataset()
    all_idx = np.arange(len(X))
    print("dataset:", X.shape)

    if "--bands" in sys.argv:
        confidence_bands(X, y_type, y_sev, rec, load)
        sys.exit()

    if "--or-positions" in sys.argv:
        or_positions()
        sys.exit()

    if "--ttd" in sys.argv:
        time_to_detect()
        sys.exit()

    if "--compare" in sys.argv:
        rows, outer, inner = [], {}, {}
        for v in VARIANTS:
            lolo = [run_fold(X, y_type, y_sev, rec, tr, te, v) for _, tr, te in lolo_splits(load, all_idx)]
            so = [run_fold(X, y_type, y_sev, rec, tr, te, v) for _, tr, te in size_out_splits(y_type, y_sev, load, all_idx)]
            outer[v] = lolo
            inner[v] = [inner_score(X, y_type, y_sev, rec, load, all_idx[load != hp], v) for hp in range(4)]
            row = (f"| {v} | {len(VARIANTS[v])} | {np.mean([r['acc'] for r in lolo]):.3f} | {np.mean([r['f1'] for r in lolo]):.3f} | "
                   f"{np.mean([r['sev_acc'] for r in lolo]):.3f} | " + " / ".join(f"{r['acc']:.3f}" for r in so)
                   + f" | {np.mean([r['acc'] for r in so]):.3f} | {np.mean([r['f1'] for r in so]):.3f} | {inner[v][3]:.3f} |")
            rows.append(row)
            print(row, flush=True)
        # nested: each outer LOLO fold picks its variant from inner CV on its own 3 training loads
        picks = [max(VARIANTS, key=lambda v: inner[v][hp]) for hp in range(4)]
        nested = [outer[p][hp] for hp, p in enumerate(picks)]
        final = max(VARIANTS, key=lambda v: inner[v][3])  # demo model trains on loads 0/1/2 -> select there
        md = "\n".join([
            "### Feature variants (seed 42, RF 300 trees, fixed hyperparameters)", "",
            "| variant | n features | LOLO acc | LOLO macro-F1 | LOLO severity acc | size-out acc (small / medium / large) | size-out acc mean | size-out macro-F1 mean | inner-CV score on loads 0/1/2 |",
            "|---|---|---|---|---|---|---|---|---|", *rows, "",
            "Inner-CV score = mean of inner-LOLO and inner-size-out fault_type macro-F1, computed on training loads only.",
            f"Nested LOLO (each outer fold picks its variant by inner CV on its 3 training loads): picks {picks}, "
            f"acc {np.mean([r['acc'] for r in nested]):.3f}, macro-F1 {np.mean([r['f1'] for r in nested]):.3f}.",
            f"Selected for the final model (inner CV on loads 0/1/2 only): **{final}**.",
        ])
        RESULTS.mkdir(exist_ok=True)
        (RESULTS / "variants.md").write_text(md + "\n", newline="\n")
        print(md)
        sys.exit()

    lolo = [(n, run_fold(X, y_type, y_sev, rec, tr, te)) for n, tr, te in lolo_splits(load, all_idx)]
    for n, r in lolo:
        print(f"LOLO {n}  acc={r['acc']:.3f}  f1={r['f1']:.3f}  sev_acc={r['sev_acc']:.3f}  baseline={r['base_acc']:.3f}")

    cond = np.array([RECORDINGS[r]["condition"] for r in rec])
    holdout = []
    for i, (tr, te) in enumerate(StratifiedGroupKFold(4, shuffle=True, random_state=SEED).split(X, cond, rec)):
        r = run_fold(X, y_type, y_sev, rec, tr, te)
        holdout.append((f"fold {i}: " + ", ".join(sorted(set(rec[te]))), r))
        print(f"holdout fold {i}  acc={r['acc']:.3f}  f1={r['f1']:.3f}  sev_acc={r['sev_acc']:.3f}")

    # Stress test: CWRU reuses one physical bearing per condition across all 4 loads, so LOLO still sees
    # the test bearing. Leaving a whole fault size out tests unseen bearings (normal is one bearing too).
    size_out = []
    for n, tr, te in size_out_splits(y_type, y_sev, load, all_idx):
        r = run_fold(X, y_type, y_sev, rec, tr, te)
        r["sev_acc"] = r["sev_base_acc"] = float("nan")  # held-out size never seen in training
        size_out.append((n, r))
        print(f"size-out {n}  acc={r['acc']:.3f}  f1={r['f1']:.3f}")

    true = np.concatenate([r["true"] for _, r in lolo])
    pred = np.concatenate([r["pred"] for _, r in lolo])
    RESULTS.mkdir(exist_ok=True)
    ConfusionMatrixDisplay(confusion_matrix(true, pred, labels=FAULT_TYPES), display_labels=FAULT_TYPES).plot(cmap="Blues", values_format="d")
    plt.title(f"fault_type, leave-one-load-out, {FINAL_VARIANT} (4 test folds pooled)")
    plt.tight_layout()
    plt.savefig(RESULTS / "confusion_lolo.png", dpi=120)

    imp = np.mean([r["importances"] for _, r in lolo], axis=0)
    top = sorted(zip(imp, VARIANTS[FINAL_VARIANT]), reverse=True)[:6]
    top_str = ", ".join(f"{n} ({v:.3f})" for v, n in top)
    print("top features:", top_str)

    md = "\n\n".join([
        f"Feature variant **{FINAL_VARIANT}** ({len(VARIANTS[FINAL_VARIANT])} features). Seed {SEED}. "
        "RandomForest(300 trees, class_weight=balanced), fixed hyperparameters (no tuning). "
        f"Windows 2048 samples, 50% overlap, {len(X)} windows from 40 recordings. "
        "Severity accuracy is on truly faulty test windows. Baselines = majority class of the training fold.",
        table("Headline: leave-one-load-out", lolo),
        table("Secondary: hold out whole recordings (StratifiedGroupKFold, 4 folds, one recording per condition per fold)", [(n.split(":")[0], r) for n, r in holdout]),
        table("Stress test: leave one fault size out (bearings never seen in training; severity n/a)", size_out),
        "Holdout folds: " + "; ".join(n for n, _ in holdout),
        f"Top fault_type features (mean RF importance over LOLO folds): {top_str}",
    ])
    (RESULTS / "results.md").write_text(md + "\n", newline="\n")
    print("wrote", RESULTS / "results.md", "and confusion_lolo.png")

"""Compare retrieval-query variants on real sensor results: python -m rag.eval.query_eval

Needs the index (python -m data.fetch_guides && python -m rag.build) and rag/eval/fixtures/scenarios.json
(python -m rag.eval.make_fixtures). Calls the real rag.retrieve, never the mock. Writes results/query_eval.md,
results/query_eval.json (chunk ids and tags only) and results/labels_audit.md. No passage text is written.
How passages are labelled: labels.json and rag/eval/README.md.
"""
import json
import os
import re
from collections import defaultdict
from pathlib import Path

from rag.interface import get_retriever
from rag.retrieve import retrieve

from .variants import VARIANTS, evidence_terms

HERE = Path(__file__).parent
RESULTS = HERE / "results"
LABELS = json.loads((HERE / "labels.json").read_text(encoding="utf-8"))
FAULTS = ("inner_race", "outer_race", "ball")
FAMILY = {"BPFI": "inner_race", "BPFO": "outer_race", "BSF": "ball"}
SAFETY = re.compile(LABELS["safety_regex"], re.I)


def derive_tags(passages):
    """chunk_id -> sorted tags (a fault name, 'normal' for a healthy-machine log, 'routine' for routine-maintenance guide pages)."""
    cites = defaultdict(set)  # (brand named in the bridge row's source, page) -> faults of the rows citing it
    for p in passages:
        if p.source_type == "playbook":
            m = re.search(r"Authoritative Source: (\w+).*?p\.\s*(\d+)", p.text)
            if m:
                cites[(m.group(1).lower(), int(m.group(2)))].add(re.search(r"Bearing Fault Type: (\S+)", p.text).group(1))
    tags = {}
    for p in passages:
        if p.source_type == "playbook":
            t = {re.search(r"Bearing Fault Type: (\S+)", p.text).group(1)}
        elif p.source_type == "log":
            t = {re.search(r"Fault Type: (\S+)", p.text).group(1)}
        else:
            where = f"{p.source_title} {p.url}".lower()  # a citation "SKF: ..., p. 12" matches any guide naming skf
            t = set().union(*[f for (b, pg), f in cites.items() if pg == p.page and b in where])
            zone = " ".join(p.text.lower().split()[:LABELS["routine_zone_words"]])
            if any(term in zone for term in LABELS["routine_terms"]):
                t.add("routine")
        tags[p.chunk_id] = sorted(t)
    stale = [c for c in LABELS["overrides"] if c not in tags]
    tags.update({c: sorted(v) for c, v in LABELS["overrides"].items() if c in tags})
    return tags, stale


def score(sensor, passages, tags):
    """Metrics for one retrieval (top 5). Decisions: see rag/eval/README.md."""
    f = sensor["fault_type"]
    t5 = [set(tags.get(p["chunk_id"], ())) for p in passages]
    good = {"normal", "routine"} if f == "normal" else {f}

    def wrong(t):
        if f == "normal":
            return bool(t & set(FAULTS)) and not t & good
        return bool(t - {"routine"}) and f not in t

    mix = {k: sum(p["source_type"] == k for p in passages) for k in ("guide", "playbook", "log")}
    return {"hit5": any(t & good for t in t5), "right5": sum(bool(t & good) for t in t5),
            "wrong3": sum(wrong(t) for t in t5[:3]), "wrong5": sum(wrong(t) for t in t5),
            "safety": None if f == "normal" else any(SAFETY.search(p["text"]) for p in passages),
            **mix,
            "synthetic_bad": sum(p["source_type"] == "log" and not (p.get("synthetic") and "SYNTHETIC" in p["text"]) for p in passages),
            "ev_fault_hit": any(FAMILY.get(e["matches"]) in t for e in sensor.get("evidence") or [] for t in t5)}


def aggregate(rows, distinct):
    n = len(rows)
    safe = [r["safety"] for r in rows if r["safety"] is not None]
    pct = lambda xs: f"{100 * sum(xs) / len(xs):.0f}%" if xs else "n/a"
    return {"n": n, "distinct": distinct, "hit5": pct([r["hit5"] for r in rows]),
            "right5": f"{sum(r['right5'] for r in rows) / n:.2f}", "wrong3": f"{sum(r['wrong3'] for r in rows) / n:.2f}",
            "wrong5": f"{sum(r['wrong5'] for r in rows) / n:.2f}", "safety": pct(safe),
            "guide": f"{sum(r['guide'] for r in rows) / n:.1f}", "playbook": f"{sum(r['playbook'] for r in rows) / n:.1f}",
            "log": f"{sum(r['log'] for r in rows) / n:.1f}", "synthetic_bad": sum(r["synthetic_bad"] for r in rows)}


def vs_a(idx, results, v):
    """Over distinct (A request, variant request) pairs in the group: how many top-5 lists changed (set / order only),
    and how many are better / worse than A on hit5, wrong3 (fewer is better), wrong5 (fewer is better)."""
    pairs = {}
    for i in idx:
        a, b = results["A"][i], results[v][i]
        pairs[(json.dumps(a["request"], sort_keys=True), json.dumps(b["request"], sort_keys=True))] = (a, b)
    pairs = list(pairs.values())
    c = lambda key, sign: sum(sign * (b["score"][key] - a["score"][key]) > 0 for a, b in pairs)
    return (f"{len(pairs)} pairs: set changed {sum(set(a['chunks']) != set(b['chunks']) for a, b in pairs)}, "
            f"order only {sum(a['chunks'] != b['chunks'] and set(a['chunks']) == set(b['chunks']) for a, b in pairs)}; "
            f"hit5 +{c('hit5', 1)}/-{c('hit5', -1)}, wrong3 +{c('wrong3', -1)}/-{c('wrong3', 1)}, wrong5 +{c('wrong5', -1)}/-{c('wrong5', 1)}")


def table(title, groups, results, note=""):
    cols = ["n", "distinct", "hit5", "right5", "wrong3", "wrong5", "safety", "guide", "playbook", "log", "synthetic_bad"]
    out = [f"### {title}", "", note, "", "| group | variant | " + " | ".join(cols) + " | vs A (distinct requests; + better / - worse) |",
           "|---|---|" + "---|" * (len(cols) + 1)]
    for g, idx in groups.items():
        if not idx:
            continue
        for v in VARIANTS:
            rows = [results[v][i]["score"] for i in idx]
            distinct = len({json.dumps(results[v][i]["request"], sort_keys=True) for i in idx})
            a = aggregate(rows, distinct)
            out.append(f"| {g} | {v} | " + " | ".join(str(a[c]) for c in cols) + " | " + ("-" if v == "A" else vs_a(idx, results, v)) + " |")
    return out + [""]


def main():
    os.environ.pop("BEARING_RAG_MOCK", None)
    r = get_retriever()
    assert r.load() and r.index.passages, "no index: run python -m data.fetch_guides && python -m rag.build"
    assert r.index.bm25 is not None and r.index.embeddings is not None, "index lacks BM25 or dense vectors, not the real retriever"
    ids = {p.chunk_id for p in r.index.passages}
    tags, stale = derive_tags(r.index.passages)
    scen = json.loads((HERE / "fixtures" / "scenarios.json").read_text(encoding="utf-8"))

    cache, results = {}, {v: [] for v in VARIANTS}
    for s in scen:
        for v, build in VARIANTS.items():
            req = build(s["sensor"])
            key = json.dumps(req, sort_keys=True)
            if key not in cache:
                cache[key] = retrieve(req)["passages"]
                assert all(p["chunk_id"] in ids for p in cache[key]), "passage not in the index: mock fallback?"
            ps = cache[key]
            results[v].append({"request": req, "chunks": [p["chunk_id"] for p in ps], "score": score(s["sensor"], ps, tags)})
    distinct = {v: len({json.dumps(x["request"], sort_keys=True) for x in results[v]}) for v in VARIANTS}

    by_tag = lambda t: [i for i, s in enumerate(scen) if t in s["tags"]]
    by_fault = lambda f, pool: [i for i in pool if scen[i]["sensor"]["fault_type"] == f]
    sweep = by_tag("sweep")
    md = ["# Query variant evaluation", "",
          "Generated by `python -m rag.eval.query_eval` (real `rag.retrieve`, top 5). Labelling rules: `rag/eval/README.md`, `labels.json`, `results/labels_audit.md`.", "",
          f"Corpus: {len(r.index.passages)} passages ({', '.join(f'{k} {sum(p.source_type == k for p in r.index.passages)}' for k in ('guide', 'playbook', 'log'))}). "
          f"Scenarios: {len(scen)} ({', '.join(f'{t} {len(by_tag(t))}' for t in ('sweep', 'hero', 'uncertain', 'conflict'))}). "
          f"Distinct requests per variant: " + ", ".join(f"{v} {n}" for v, n in distinct.items()) + ".", "",
          "Metrics: hit5 = share of scenarios with a passage about the predicted fault in the top 5; right5 = mean number of top-5 passages about it; wrong3/wrong5 = mean number of top-3/top-5 passages about a different fault; "
          "safety = share of faulty scenarios with a lockout/isolation/de-energise step in the top 5; guide/playbook/log = mean passages of that source type in the top 5; "
          "synthetic_bad = log passages not flagged synthetic (must be 0). Scenarios in a group share requests: `distinct` is the number of different requests, and the vs-A counts are over distinct request pairs, not scenarios.", ""]
    md += table("Sweep, by predicted fault type (6 evenly spaced windows per held-out recording)",
                {**{f: by_fault(f, sweep) for f in ("normal", *FAULTS)}, "all": sweep}, results)
    md += table("Sweep, faulty scenarios by predicted severity",
                {f"{sev}": [i for i in sweep if scen[i]["sensor"]["fault_type"] != "normal" and scen[i]["sensor"]["severity"] == sev]
                 for sev in ("small", "medium", "large")}, results)
    md += table("Hero, uncertain and conflict picks", {t: by_tag(t) for t in ("hero", "uncertain", "conflict")}, results,
                "Scored against the predicted fault type, as everywhere. In `uncertain` window 114 is predicted ball although the recording is outer race.")

    md += ["### Per-scenario detail: hero, uncertain, conflict", "",
           "Each cell: hit5 / wrong3 / safety (1 = yes). `ev` lists the evidence families; `true` is the recording's real fault.", "",
           "| scenario | tags | predicted (conf) | true | ev | " + " | ".join(VARIANTS) + " |", "|---|---|---|---|---|" + "---|" * len(VARIANTS)]
    for i, s in enumerate(scen):
        if set(s["tags"]) & {"hero", "uncertain", "conflict"} or s["sensor"]["fault_type"] != s["true_fault"]:
            x = s["sensor"]
            ev = ",".join(dict.fromkeys(e["matches"] for e in x["evidence"])) or "-"
            cells = [f"{int(results[v][i]['score']['hit5'])}/{results[v][i]['score']['wrong3']}/{int(bool(results[v][i]['score']['safety']))}" for v in VARIANTS]
            md.append(f"| {s['id']} | {','.join(s['tags'])} | {x['fault_type']}/{x['severity']} ({x['confidence']}) | {s['true_fault']} | {ev} | " + " | ".join(cells) + " |")
    md.append("")

    md += ["### Conflict windows: what each variant retrieves", "",
           "No special handling: the request is built exactly as the variant says. Tags in brackets (untagged = general). `ev-fault passages` = top-5 passages about the family the evidence points at.", ""]
    for i in by_tag("conflict"):
        s = scen[i]
        md += [f"**{s['id']}**: classifier {s['sensor']['fault_type']} ({s['sensor']['confidence']}), evidence "
               + ", ".join(f"{e['matches']} x{e['vs_normal']}" for e in s["sensor"]["evidence"]), ""]
        for v in VARIANTS:
            x = results[v][i]
            md.append(f"- {v}: `{x['request']['query']}` (severity {x['request']['severity']})  \n  "
                      + " | ".join(f"{c} [{','.join(tags[c]) or 'general'}]" for c in x["chunks"]))
        md.append("")
    if stale:
        md += [f"Stale overrides in labels.json (chunk ids not in this corpus): {stale}", ""]

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "query_eval.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    rows = [{"id": s["id"], "tags": s["tags"], "variants": {v: {"request": results[v][i]["request"], "chunks": results[v][i]["chunks"],
                                                                 "score": results[v][i]["score"]} for v in VARIANTS}} for i, s in enumerate(scen)]
    (RESULTS / "query_eval.json").write_text("[\n" + ",\n".join(json.dumps(x) for x in rows) + "\n]\n", encoding="utf-8", newline="\n")  # one scenario per line
    audit = ["# Label audit (derived by derive_tags from labels.json and the current index)", "",
             "| chunk_id | source | page | type | tags |", "|---|---|---|---|---|"]
    audit += [f"| {p.chunk_id} | {p.source_title} | {p.page} | {p.source_type} | {', '.join(tags[p.chunk_id]) or 'general'} |" for p in r.index.passages]
    (RESULTS / "labels_audit.md").write_text("\n".join(audit) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()

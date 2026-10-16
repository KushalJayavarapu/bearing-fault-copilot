"""Try several models on the same prompt and score them:   python -m app.api.llm_compare [--models a,b] [--runs 2] [--rag]

Why: on 15 Oct the default model put a stray ")Skip" into every explanation and once said the evidence list was empty
while a strong peak was listed. Choose the model by measuring, not by guessing.

Each call is scored like a real request: valid JSON, our text checks (stray text, "no evidence" claims), at least one
action, and no invented citation ids. Latency is printed too. Models that spend max_tokens on thinking (Qwen, GLM, MiMo)
are skipped unless you name them with --models. The whole team shares 20 requests per minute, so calls are spaced out.
"""
import argparse
import re
import statistics
import sys
import time

from . import mock_data, orchestrator, prompt, retrieval_stub, uncertainty
from .envfile import load_env
from .llm import LLMClient, LLMError

THINKING = re.compile(r"qwen|glm|mimo|thinking|reason|r1\b", re.I)
CASES = [("OR007@6_3", 2),  # medium confidence, strong outer race peak: the case that failed on 15 Oct
         ("OR007@6_3", 0)]  # same recording, 57% confidence: high uncertainty (hedged text, manual inspection first)
GAP_S = 4.0


def run_once(llm, sensor, passages):
    """One call, scored: {"ok": bool, "ms": int, "problem": str}."""
    level = uncertainty.level(sensor["confidence"])
    messages = prompt.build_messages(sensor, level, orchestrator.evidence_conflict(sensor), passages)
    try:
        reply = llm.chat(messages, max_tokens=orchestrator.MAX_TOKENS)
    except LLMError as e:
        return {"ok": False, "ms": 0, "problem": f"call failed: {e}"[:90]}
    try:
        parts, dropped = prompt.parse_output(reply.text, {p["chunk_id"] for p in passages})
        prompt.check_text(parts, sensor)
    except prompt.BadOutput as e:
        return {"ok": False, "ms": reply.latency_ms, "problem": str(e)[:90]}
    problem = "no supported action" if not parts["recommended_actions"] else f"{dropped} invented citation(s)" if dropped else ""
    return {"ok": not problem, "ms": reply.latency_ms, "problem": problem}


def summarize(results):
    """results: {model: [run_once results]} -> (rows, best model or None). Best = most ok runs, then fastest median."""
    rows = []
    for model, runs in results.items():
        times = [r["ms"] for r in runs if r["ms"]]
        rows.append({"model": model, "ok": sum(r["ok"] for r in runs), "n": len(runs),
                     "median_ms": round(statistics.median(times)) if times else None,
                     "problems": sorted({r["problem"] for r in runs if r["problem"]})})
    good = [r for r in rows if r["ok"] > 0]
    best = min(good, key=lambda r: (-r["ok"], r["median_ms"] or 10 ** 9))["model"] if good else None
    return rows, best


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--models", help="comma-separated model ids (default: the current LLM_MODEL plus up to 3 others)")
    ap.add_argument("--runs", type=int, default=2, help="calls per model and case (default 2)")
    ap.add_argument("--rag", action="store_true", help="use the real retrieval (rag/) instead of the stub passages")
    args = ap.parse_args(argv)
    load_env()
    try:
        llm = LLMClient.from_env()
    except LLMError as e:
        print(f"FAIL: {e}")
        return 1
    current = llm.model
    if args.models:
        models = [m.strip() for m in args.models.split(",") if m.strip()]
    else:
        try:
            others = [m for m in llm.list_models() if m and m != current and not THINKING.search(m)]
        except Exception as e:
            print(f"(could not list models: {e}; testing only {current})")
            others = []
        models = [current] + others[:3]
    total = len(models) * len(CASES) * args.runs
    print(f"{len(models)} model(s) x {len(CASES)} case(s) x {args.runs} run(s) = {total} calls, about {round(total * GAP_S)} s "
          f"(the team shares 20 requests per minute: tell them before you start)\n")
    results = {m: [] for m in models}
    first = True
    for model in models:
        llm.model, llm.json_mode = model, True
        for rid, idx in CASES:
            sensor = mock_data.sensor_result(rid, idx)
            if args.rag:
                from rag.retrieve import retrieve
                passages = retrieve(orchestrator.build_query(sensor))["passages"]
            else:
                passages = retrieval_stub.retrieve(orchestrator.build_query(sensor))["passages"]
            for _ in range(args.runs):
                if not first:
                    time.sleep(GAP_S)
                first = False
                r = run_once(llm, sensor, passages)
                results[model].append(r)
                print(f"{model:<32} {rid} w{idx:<3} {'ok  ' if r['ok'] else 'FAIL'} {r['ms']:>6} ms  {r['problem']}", flush=True)
    rows, best = summarize(results)
    print("\nSummary")
    for r in sorted(rows, key=lambda r: (-r["ok"], r["median_ms"] or 10 ** 9)):
        print(f"  {r['model']:<32} ok {r['ok']}/{r['n']}   median {r['median_ms']} ms   {'; '.join(r['problems'])}")
    if best:
        print(f"\nBest on this test: {best}.  To use it: set LLM_MODEL={best} in .env and restart the app.")
        print("Two runs per case is a small sample: check the winner again with a few real /analyze calls.")
    else:
        print("\nNo model produced a usable answer. Run python -m app.api.llm_smoke to see why.")
    return 0 if best else 1


if __name__ == "__main__":
    sys.exit(main())

"""Sensor result -> retrieval -> LLM -> checked final answer (contract section 3).

Rules enforced here, not left to the model:
- sensor result, uncertainty, citations, needs_human_confirm and meta are built by us
- citations only come from retrieved passages; actions the passages do not support are dropped
- no retrieved passages = the LLM is not asked (nothing to ground on)
- LLM down or unusable output = a degraded answer (sensor result + manual inspection), never a crash
- evidence that disagrees with the classifier is shown, and uncertainty can then not be "low"
"""
import logging
import os
import time

from . import prompt, uncertainty
from .llm import LLMError

log = logging.getLogger("app.orchestrator")
# Page numbers are shown only if CITE_PAGES=true. Our guide texts are team-written and their page markers are not pages of
# any real document (the bridge table's "p. 34" is a page in a vendor manual we have not checked), so by default no page
# is shown, to the model or in a citation. Also, some passages carry a text page ("bridge-table", "L001"), which the
# contract (page is a number or null) cannot hold.
CITE_PAGES = os.environ.get("CITE_PAGES", "false").strip().lower() == "true"
MAX_TOKENS = 700  # the answer is a few short sentences; a lower cap keeps a slow gateway from stretching the wait

FAMILY = {"BPFI": "inner_race", "BPFO": "outer_race", "BSF": "ball"}
MANUAL = {"step": "Arrange a manual inspection of the bearing before relying on this result.",
          "safety_critical": False, "citation_ids": []}
DEGRADED = {
    "no_passages": "No supporting reference passages were found, so only the sensor result is shown.",
    "llm_error": "The explanation service did not respond, so only the sensor result is shown.",
    "bad_output": "The explanation could not be checked, so only the sensor result is shown.",
}


def build_query(sensor):
    """Retrieval request (contract section 2)."""
    ft, sev = sensor["fault_type"], sensor["severity"]
    q = ("healthy deep groove ball bearing: routine condition monitoring and when to act" if ft == "normal"
         else f"{ft.replace('_', ' ')} defect, {sev}, deep groove ball bearing: causes and actions")
    return {"query": q, "fault_type": ft, "severity": sev, "top_k": 5}


def evidence_conflict(sensor):
    """Sentence describing a disagreement between the vibration evidence and the classifier, or None."""
    strong = [e for e in sensor.get("evidence") or []
              if e.get("matches") in FAMILY and e.get("strength") in ("medium", "high")]
    if not strong:
        return None
    best = max(strong, key=lambda e: e.get("vs_normal", 0))
    family = FAMILY[best["matches"]]
    if family == sensor["fault_type"]:
        return None
    return (f"The strongest vibration peak matches {family.replace('_', ' ')} ({best['matches']}), "
            f"but the classifier says {sensor['fault_type'].replace('_', ' ')}.")


def _scrub(p):
    page = p.get("page")
    keep = CITE_PAGES and isinstance(page, int) and not isinstance(page, bool)
    return {**p, "page": page if keep else None}


def _ms(since):
    return round((time.perf_counter() - since) * 1000)


def _ask(llm, sensor, level, conflict, passages):
    """Return (parts, model, llm_ms, failure). One repair attempt if the answer is unusable."""
    messages = prompt.build_messages(sensor, level, conflict, passages)
    allowed, total_ms, model = {p["chunk_id"] for p in passages}, 0, getattr(llm, "model", "unknown")
    for attempt in range(2):
        try:
            reply = llm.chat(messages, max_tokens=MAX_TOKENS)
        except LLMError as e:
            log.warning("LLM call failed, showing the degraded answer: %s", e)
            return None, "unavailable", total_ms, "llm_error"
        total_ms += reply.latency_ms
        if reply.model != model:  # the gateway names models its own way (it once said "self-dploy/..."): show ours
            log.info("gateway reports model %r for configured model %r", reply.model, model)
        try:
            parts, _dropped = prompt.parse_output(reply.text, allowed)
            prompt.check_text(parts, sensor)
            return parts, model, total_ms, None
        except prompt.BadOutput as e:
            log.warning("LLM answer rejected (attempt %d of 2): %s", attempt + 1, e)
            messages = messages + [{"role": "assistant", "content": reply.text},
                                   {"role": "user", "content": f"That answer was not usable ({e}). "
                                                               "Answer again with only the JSON object."}]
    return None, model, total_ms, "bad_output"


def analyze(sensor, *, retrieve, llm, request_id, classifier_ms=0, served_on="unknown"):
    t0 = time.perf_counter()
    conflict = evidence_conflict(sensor)
    level = uncertainty.level(sensor["confidence"])
    if conflict and level == "low":
        level = "medium"
    note = uncertainty.note(level, sensor["confidence"]) + (f" {conflict}" if conflict else "")

    t = time.perf_counter()
    try:
        passages = [_scrub(p) for p in retrieve(build_query(sensor)).get("passages", []) if p.get("chunk_id")]
    except Exception as e:  # retrieval down: answer from the sensor alone
        log.warning("retrieval failed, answering from the sensor alone: %s: %s", type(e).__name__, e)
        passages = []
    retrieval_ms = _ms(t)

    parts, model, llm_ms, failure = None, "unavailable", 0, "no_passages"
    if passages:
        parts, model, llm_ms, failure = _ask(llm, sensor, level, conflict, passages)

    if parts is None:
        explanation, causes, actions = DEGRADED[failure], [], [dict(MANUAL)]
        note += " The written explanation is unavailable."
    else:
        explanation, causes, actions = parts["explanation"], parts["likely_causes"], parts["recommended_actions"]
        if level == "high":
            if prompt.needs_hedge(explanation):
                explanation = prompt.HEDGE + explanation
            actions.insert(0, dict(MANUAL))
        elif not actions:
            actions = [dict(MANUAL)]

    by_id = {p["chunk_id"]: p for p in passages}
    cited = list(dict.fromkeys(i for a in actions for i in a["citation_ids"]))
    citations = []
    for i in cited:
        p = by_id[i]
        text = p.get("excerpt") or p.get("text", "")  # retrieval's focused sentence if it gives one
        title = p.get("source_title", "")
        if p.get("synthetic"):  # made-up example data (e.g. the sample maintenance logs) must never look like a real source
            title = f"[Synthetic example] {title}"
        citations.append({"id": i, "source_title": title, "page": p.get("page"),
                          "url": p.get("url") or "", "excerpt": text[:237] + "..." if len(text) > 240 else text})
    return {
        "request_id": request_id,
        "sensor": sensor,
        "explanation": explanation,
        "likely_causes": causes,
        "recommended_actions": actions,
        "needs_human_confirm": parts is None or level == "high" or any(a["safety_critical"] for a in actions),
        "citations": citations,
        "uncertainty": {"level": level, "note": note},
        "meta": {"model": model, "served_on": served_on,
                 "latency_ms": {"classifier": classifier_ms, "retrieval": retrieval_ms, "llm": llm_ms,
                                "total": classifier_ms + _ms(t0)}},
    }

"""Query variants compared by rag.eval.query_eval. Each takes a sensor result and returns a retrieval request.

A  orchestrator.build_query as it is today (imported, not copied)
B  A without the severity word in the query text (request still carries severity, which rag.retriever
   also puts into one of its own sub-queries)
B2 B and severity=None in the request (extra: removes severity everywhere)
C  A plus evidence terms when sensor["evidence"] is non-empty
D  C plus the bridge-table damage-mode names for the predicted fault type
"""
import re
from functools import lru_cache
from pathlib import Path

from app.api.orchestrator import build_query as A
from rag.parser import ingest_bridge_table

BRIDGE = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "bridge_table.md"
# evidence "matches" -> words for the family it points at (same mapping as orchestrator.FAMILY)
EVIDENCE_WORDS = {"BPFI": "inner race", "BPFO": "outer race", "BSF": "ball"}


def B(sensor):
    req = A(sensor)
    if sensor["fault_type"] != "normal":  # A's normal query has no severity word
        stripped = req["query"].replace(f", {sensor['severity']}", "", 1)
        assert stripped != req["query"], req["query"]
        req["query"] = stripped
    return req


def B2(sensor):
    return {**B(sensor), "severity": None}


def evidence_terms(sensor):
    """'outer race fault frequency BPFO, repeating impacts' for each distinct family in the evidence, strongest first."""
    fams = list(dict.fromkeys(e["matches"] for e in sensor.get("evidence") or [] if e.get("matches") in EVIDENCE_WORDS))
    return "; ".join(f"{EVIDENCE_WORDS[f]} fault frequency {f}, repeating impacts" for f in fams)


def C(sensor):
    req, terms = A(sensor), evidence_terms(sensor)
    if terms:
        req["query"] += "; " + terms
    return req


@lru_cache(maxsize=1)
def _damage_modes():
    modes = {}
    for p in ingest_bridge_table(BRIDGE):
        fault = re.search(r"Bearing Fault Type: (\S+)", p.text).group(1)
        modes.setdefault(fault, []).append(re.search(r"Damage Mode: (.+)", p.text).group(1).strip())
    return modes


def D(sensor):
    req, modes = C(sensor), _damage_modes().get(sensor["fault_type"], [])
    if modes:
        req["query"] += "; " + "; ".join(modes)
    return req


VARIANTS = {"A": A, "B": B, "B2": B2, "C": C, "D": D}

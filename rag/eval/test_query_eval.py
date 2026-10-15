"""Self-check for the labeller, scorer and variants: python -m rag.eval.test_query_eval (no index needed)."""
from rag.models import Passage

from .query_eval import derive_tags, score
from .variants import A, B, B2, C, D, evidence_terms


def P(cid, typ, text, title="X", page=1, url="u"):
    return Passage(chunk_id=cid, text=text, source_title=title, source_type=typ, page=page, url=url)


def run():
    ps = [P("b1", "playbook", "Bearing Fault Type: inner_race\nDamage Mode: m\nAuthoritative Source: SKF: Guide, p. 12"),
          P("l1", "log", "Fault Type: normal\nNotice: [SYNTHETIC DEMO LOG]", page="L1"),
          P("g12", "guide", "Spalling inner ring text", title="SKF: Guide", page=12, url="https://www.skf.com/x"),
          P("g13", "guide", "Other page", title="SKF: Guide", page=13),
          P("g1", "guide", "Routine greasing and condition monitoring basics", title="Motor", page=1)]
    tags, stale = derive_tags(ps)
    assert tags == {"b1": ["inner_race"], "l1": ["normal"], "g12": ["inner_race"], "g13": [], "g1": ["routine"]} and not stale, tags

    def hit(fault, ids, safe="x"):
        got = [{"chunk_id": i, "source_type": "guide", "text": safe} for i in ids]
        return score({"fault_type": fault, "evidence": []}, got, tags)

    assert hit("inner_race", ["g12", "g13"])["hit5"] and hit("inner_race", ["g12", "g13"])["wrong3"] == 0
    assert hit("outer_race", ["g12", "b1", "g13"])["wrong3"] == 2 and not hit("outer_race", ["g12"])["hit5"]
    assert hit("inner_race", ["g1", "l1"])["wrong3"] == 1  # routine page is neutral, a healthy-machine log is not
    assert hit("normal", ["g1"])["hit5"] and hit("normal", ["g12"])["wrong3"] == 1
    assert hit("inner_race", ["g12"], "Safety-Critical Action: Yes (lock out)")["safety"] and not hit("inner_race", ["g12"])["safety"]

    s = {"fault_type": "outer_race", "severity": "small",
         "evidence": [{"matches": "BPFO"}, {"matches": "BPFO"}, {"matches": "BSF"}]}
    assert evidence_terms(s) == ("outer race fault frequency BPFO, repeating impacts; ball fault frequency BSF, repeating impacts")
    assert A(s)["query"] == "outer race defect, small, deep groove ball bearing: causes and actions"
    assert B(s)["query"] == "outer race defect, deep groove ball bearing: causes and actions" and B(s)["severity"] == "small"
    assert B2(s)["severity"] is None
    assert C(s)["query"].startswith(A(s)["query"] + "; outer race fault frequency BPFO")
    assert D(s)["query"].startswith(C(s)["query"] + "; ") and len(D(s)["query"]) > len(C(s)["query"])
    h = {"fault_type": "normal", "severity": "none", "evidence": []}
    assert A(h) == B(h) == C(h) == D(h)  # healthy: no severity word, no evidence, no damage modes
    print("ok")


if __name__ == "__main__":
    run()

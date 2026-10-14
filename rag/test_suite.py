"""
Script to test Kushal's 10 orchestrator queries and Atharva's 12 independent questions.
"""

from rag.retrieve import retrieve
import json
from pathlib import Path

ORCHESTRATOR_QUERIES = [
    {"query": "normal bearing, healthy baseline: causes and actions", "fault_type": "normal", "severity": "none"},
    {"query": "inner race defect, small, deep groove ball bearing: causes and actions", "fault_type": "inner_race", "severity": "small"},
    {"query": "inner race defect, medium, deep groove ball bearing: causes and actions", "fault_type": "inner_race", "severity": "medium"},
    {"query": "inner race defect, large, deep groove ball bearing: causes and actions", "fault_type": "inner_race", "severity": "large"},
    {"query": "outer race defect, small, deep groove ball bearing: causes and actions", "fault_type": "outer_race", "severity": "small"},
    {"query": "outer race defect, medium, deep groove ball bearing: causes and actions", "fault_type": "outer_race", "severity": "medium"},
    {"query": "outer race defect, large, deep groove ball bearing: causes and actions", "fault_type": "outer_race", "severity": "large"},
    {"query": "ball defect, small, deep groove ball bearing: causes and actions", "fault_type": "ball", "severity": "small"},
    {"query": "ball defect, medium, deep groove ball bearing: causes and actions", "fault_type": "ball", "severity": "medium"},
    {"query": "ball defect, large, deep groove ball bearing: causes and actions", "fault_type": "ball", "severity": "large"},
]


def test_orchestrator_queries():
    print("=" * 70)
    print("Testing Kushal's 10 Orchestrator Generated Queries")
    print("=" * 70)

    for i, q in enumerate(ORCHESTRATOR_QUERIES, 1):
        res = retrieve(q)
        passages = res.get("passages", [])
        if not passages:
            print(f"[{i:02d}] FAILED: No passages returned for {q['fault_type']} / {q['severity']}")
            continue
        
        top = passages[0]
        # Verify citation fields
        has_citations = all(k in top and top[k] for k in ["source_title", "page", "url", "chunk_id"])
        status = "PASS" if has_citations else "FAIL (missing metadata)"
        print(f"[{status}] {i:02d}. {q['fault_type']}/{q['severity']}:")
        print(f"       Top: {top['chunk_id']} | Source: {top['source_title']} (p. {top['page']})")
        print(f"       Snippet: {top.get('excerpt', top['text'][:80])}")
        print(f"       Total candidates returned: {len(passages)}\n")


def test_atharva_independent_set():
    print("=" * 70)
    print("Testing Atharva's 12 Independent Maintenance Questions")
    print("=" * 70)

    eval_file = Path("data/knowledge/eval_questions.json")
    if not eval_file.exists():
        print("eval_questions.json not found.")
        return

    with open(eval_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    hits = 0
    for q in questions:
        req = {
            "query": q["question"],
            "fault_type": q.get("fault_type"),
            "severity": q.get("severity"),
            "top_k": 5
        }
        res = retrieve(req)
        passages = res.get("passages", [])

        expected_pages = q.get("expected_pages", [q.get("expected_page")])
        is_hit = False
        hit_id = None
        for p in passages:
            p_chunk = p.get("chunk_id", "")
            p_page = p.get("page")
            if p_page in expected_pages or any(str(ep) in str(p_page) for ep in expected_pages) or q.get("expected_guide", "") in p_chunk:
                is_hit = True
                hit_id = p_chunk
                break

        if is_hit:
            hits += 1
            status = "HIT "
        else:
            status = "MISS"

        print(f"[{status}] {q['id']}: {q['question'][:50]}... -> {hit_id or 'None'}")

    hit_rate = (hits / len(questions)) * 100.0
    print(f"\nAtharva Independent Set Hit Rate: {hit_rate:.1f}% ({hits}/{len(questions)})")


if __name__ == "__main__":
    test_orchestrator_queries()
    test_atharva_independent_set()

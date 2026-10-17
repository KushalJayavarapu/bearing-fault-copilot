# rag/ - Bearing Fault Retrieval-Augmented Generation Pipeline

**Owner:** Santos (RAG Pipeline)  
**Deliverable:** Ingest, chunk, embed, index, and retrieve passages with source metadata over the team's bearing reference notes, the bridge table, and synthetic maintenance logs.  
**Compliance:** Adheres strictly to `docs/contract.md` (v0.1 section 2).

---

## 1. Orchestrator Integration

Kushal's orchestrator imports a single function:

```python
from rag.retrieve import retrieve

# Standard contract call (request dictionary)
result = retrieve({
    "query": "outer race defect, small, deep groove ball bearing: causes and actions",
    "fault_type": "outer_race",
    "severity": "small",
    "top_k": 5
})
```

### Mock Mode

For zero-dependency unit tests or frontend development:
```python
result = retrieve({"use_mock": True})
# Or set environment variable:
# export BEARING_RAG_MOCK=1
```

### Response Shape (`docs/contract.md` Section 2)

```json
{
  "passages": [
    {
      "chunk_id": "bridge-table-outer_race-p34-c5",
      "text": "Bearing Fault Type: outer_race\nDamage Mode: Subsurface initiated spalling...",
      "source_title": "Curated Bearing Fault Bridge Table",
      "source_type": "playbook",
      "page": 34,
      "url": "data/knowledge/bridge_table.md",
      "excerpt": "Inspect outer ring load zone pattern; support rotor/housing weight before loosening mount bolts."
    }
  ]
}
```

---

## 2. Docker & Image Build Commands

Search indices are stored under `rag/index/`, which is git-ignored and not committed. Docker builds the index at image build time with:

```dockerfile
# 1. Fetch / extract local guide texts
RUN python -m data.fetch_guides

# 2. Build hybrid BM25 + ONNX dense vector index
RUN python -m rag.build
```

### Manual Index Rebuild

```bash
python -m rag.build
```

---

## 3. Benchmark & Verification Results

The retrieval engine has been evaluated across three distinct query suites:

### Suite A: Kushal's 10 Orchestrator Queries (1 per fault and size)
All 10 queries synthesized by the orchestrator were evaluated:
- `normal / none` (healthy baseline check)
- `inner_race / small (0.007")`
- `inner_race / medium (0.014")`
- `inner_race / large (0.021")`
- `outer_race / small (0.007")`
- `outer_race / medium (0.014")`
- `outer_race / large (0.021")`
- `ball / small (0.007")`
- `ball / medium (0.014")`
- `ball / large (0.021")`

**Result: 10 / 10 PASS (0 failures)**. Every query returns 5 passages with valid `source_title`, `page`, `url`, `chunk_id`, and lead `excerpt`.

### Suite B: Atharva's Test Set (`data/knowledge/eval_questions.json`)
12 questions written by a teammate other than the retriever's author (still our own team, not an external benchmark) testing specific technical details (fatigue initiation depth, 6 o'clock load zone rotation, ball skidding mitigation, VFD fluting insulation, true brinelling vs false brinelling, and motor LOTO safety).

**Result: 12 / 12 (100.0% Top-5 Hit Rate)**.

### Suite C: Santos's Comprehensive Diagnostic Test Set (`rag/evaluate.py`)
18 questions across Causes, Symptoms, Actions, and Safety.

**Result: 18 / 18 (100.0% Top-5 Hit Rate, 42.5 ms average latency)**.

---

## 4. Architecture Summary

```text
       [Classifier Result / Technician Query]
                         │
                         ▼
        ┌──────────────────────────────────┐
        │     Query Expansion Engine       │
        │  • Root causes & failure modes   │
        │  • Symptoms & damage patterns    │
        │  • Corrective actions & safety   │
        └─────────────────┬────────────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
   ┌─────────────────┐         ┌─────────────────┐
   │   BM25 Search   │         │  Dense Vectors  │
   │   (Rank-BM25)   │         │ (BGE-Small ONNX)│
   └────────┬────────┘         └────────┬────────┘
            │                           │
            └─────────────┬─────────────┘
                          │
                          ▼
        ┌──────────────────────────────────┐
        │  Reciprocal Rank Fusion (RRF)    │
        │   + Page-level Deduplication     │
        └─────────────────┬────────────────┘
                          │
                          ▼
            [Top-5 Passages with Citations]
                          │
                          ▼
            [Prompt Helper for Kushal's LLM]
```

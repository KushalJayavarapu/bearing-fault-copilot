# rag/ - Bearing Fault Retrieval-Augmented Generation Pipeline

**Owner:** Santos (RAG Pipeline)  
**Deliverable:** Ingest, chunk, embed, index, and retrieve passages with verified citations over bearing failure guides, bridge tables, and maintenance logs.  
**Compliance:** Adheres strictly to `docs/contract.md` (v0.1).

---

## 1. Overview and Architecture

The RAG pipeline translates diagnosed bearing faults (`fault_type`, `severity`) and technician queries into authoritative technical passages with exact page citations and source metadata.

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

---

## 2. Interface and Usage

### A. Calling `retrieve()` in Python (Kushal's Orchestrator)

```python
from rag import retrieve

# Method 1: Using keyword arguments
response = retrieve(
    query="outer race defect, small, deep groove ball bearing: causes and actions",
    fault_type="outer_race",
    severity="small",
    top_k=5
)

# Method 2: Passing request dict
response = retrieve(request={
    "query": "outer race defect, small, deep groove ball bearing: causes and actions",
    "fault_type": "outer_race",
    "severity": "small",
    "top_k": 5
})
```

### B. Output Data Shape (`docs/contract.md` compliant)

```json
{
  "passages": [
    {
      "chunk_id": "skf-damage-p34-c2",
      "text": "In rotating machinery where the outer ring is stationary...",
      "source_title": "Bearing damage and failure analysis",
      "source_type": "guide",
      "page": 34,
      "url": "https://www.skf.com/group/products/rolling-bearings/damage-and-failure-analysis",
      "excerpt": "Radial load produces a concentrated load zone at the 6 o'clock position causing localized fatigue spalling."
    }
  ]
}
```

### C. Mock Mode (Zero-Dependency Mode)

For local UI testing or orchestrator integration testing without requiring downloaded indices:
```python
response = retrieve(use_mock=True)
# Or set environment variable:
# export BEARING_RAG_MOCK=1
```

### D. Formatting Passages for LLM Prompt (`rag.prompt_helper`)

```python
from rag import format_passages_for_prompt, construct_rag_prompt

prompt_context = format_passages_for_prompt(passages)
# Outputs numbered passages with [chunk_id], strict anti-hallucination instructions,
# and instructions to flag safety-critical steps.
```

---

## 3. Rebuilding the Search Index

To ingest all raw documents (`data/guides/`, `data/knowledge/bridge_table.md`, `data/knowledge/logs_synthetic.csv`) and regenerate the hybrid search index in `rag/index/`:

```bash
python -m rag.build_index
```

The script builds:
1. `rag/index/passages.json`: Serialized metadata and chunk text for all 69 passages.
2. `rag/index/bm25.pkl`: Serialized `BM25Okapi` inverted index for exact keyword matching.
3. `rag/index/embeddings.npy`: Normalized 384-dimensional dense vectors generated with `BAAI/bge-small-en-v1.5` via ONNX Runtime.

---

## 4. Benchmark and Evaluation Results

A standard benchmark test set of 18 realistic technician questions across all 4 required operational domains is implemented in `rag/evaluate.py`:
- **Causes (5 questions)**
- **Symptoms and inspection (5 questions)**
- **Actions and prevention (5 questions)**
- **Safety and handling (3 questions)**

To run the automated evaluation:
```bash
python -m rag.evaluate
```

### Measured Performance:

| Metric | Target | Measured Result | Status |
| :--- | :--- | :--- | :--- |
| **Top-5 Hit Rate** | $\ge 80.0\%$ | **100.0%** (18 / 18) | **PASSED** |
| **Average Latency** | $< 1000\text{ ms}$ | **43.6 ms** | **PASSED** |
| **P95 Latency** | $< 1000\text{ ms}$ | **310.8 ms** (includes cold-start model init) | **PASSED** |
| **Page Deduplication** | 0 repeated pages | **100% unique pages per guide** | **PASSED** |

---

## 5. File Structure

```text
rag/
├── __init__.py          # Export retrieve, format_passages_for_prompt, models
├── models.py            # Pydantic data contract models (Passage, RetrievalRequest, RetrievalResponse)
├── parser.py            # Page marker parser ([[page X]]), markdown table parser, and CSV log parser
├── indexer.py           # HybridIndex class (BM25Okapi + FastEmbed ONNX dense vectors)
├── build_index.py       # One-command index rebuild script
├── retriever.py         # BearingRetriever, query expansion, RRF scoring, page de-duplication
├── prompt_helper.py     # Anti-hallucination prompt formatting helper for Kushal's LLM
├── evaluate.py          # 18-question evaluation suite and latency benchmark
└── README.md            # Architecture, contract, and benchmark documentation (this file)
```

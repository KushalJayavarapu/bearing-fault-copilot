"""
Indexer for Bearing Fault Copilot RAG pipeline.
Builds and persists hybrid BM25 and Dense Vector indices.
"""

import json
import pickle
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

try:
    from fastembed import TextEmbedding
except ImportError:
    TextEmbedding = None

from .models import Passage

MODEL_NAME = "BAAI/bge-small-en-v1.5"


def tokenize_text(text: str) -> List[str]:
    """Tokenize and normalize text for BM25."""
    clean = re.sub(r"[^\w\s-]", " ", text.lower())
    tokens = clean.split()
    return tokens


class HybridIndex:
    def __init__(self, index_dir: Path):
        self.index_dir = index_dir
        self.passages: List[Passage] = []
        self.bm25: Optional[BM25Okapi] = None
        self.embeddings: Optional[np.ndarray] = None
        self.embed_model = None

    def _get_embed_model(self):
        if self.embed_model is None and TextEmbedding is not None:
            self.embed_model = TextEmbedding(model_name=MODEL_NAME)
        return self.embed_model

    def build(self, passages: List[Passage]):
        self.passages = passages
        texts = [p.text for p in passages]

        print(f"Building BM25 index over {len(passages)} passages...")
        tokenized_corpus = [tokenize_text(t) for t in texts]
        if BM25Okapi is not None:
            self.bm25 = BM25Okapi(tokenized_corpus)
        else:
            print("WARNING: rank_bm25 not installed.")

        print(f"Computing dense vector embeddings using {MODEL_NAME}...")
        embed_model = self._get_embed_model()
        if embed_model is not None:
            raw_embs = list(embed_model.embed(texts))
            embs = np.array(raw_embs, dtype=np.float32)
            # Normalize vectors for cosine similarity
            norms = np.linalg.norm(embs, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self.embeddings = embs / norms
        else:
            print("WARNING: TextEmbedding not available, dense indexing skipped.")

    def save(self):
        self.index_dir.mkdir(parents=True, exist_ok=True)
        # 1. Passages metadata
        passages_file = self.index_dir / "passages.json"
        passages_data = [p.model_dump() for p in self.passages]
        with open(passages_file, "w", encoding="utf-8") as f:
            json.dump(passages_data, f, indent=2)

        # 2. BM25
        if self.bm25 is not None:
            bm25_file = self.index_dir / "bm25.pkl"
            with open(bm25_file, "wb") as f:
                pickle.dump(self.bm25, f)

        # 3. Dense embeddings
        if self.embeddings is not None:
            emb_file = self.index_dir / "embeddings.npy"
            np.save(emb_file, self.embeddings)

        print(f"Hybrid index saved to {self.index_dir}")

    def load(self) -> bool:
        passages_file = self.index_dir / "passages.json"
        if not passages_file.exists():
            return False

        with open(passages_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.passages = [Passage(**item) for item in data]

        bm25_file = self.index_dir / "bm25.pkl"
        if bm25_file.exists():
            with open(bm25_file, "rb") as f:
                self.bm25 = pickle.load(f)

        emb_file = self.index_dir / "embeddings.npy"
        if emb_file.exists():
            self.embeddings = np.load(emb_file)

        return True

    def search_bm25(self, query: str, top_k: int = 15) -> List[Tuple[int, float]]:
        if self.bm25 is None or not self.passages:
            return []
        q_tokens = tokenize_text(query)
        scores = self.bm25.get_scores(q_tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]

    def search_dense(self, query: str, top_k: int = 15) -> List[Tuple[int, float]]:
        if self.embeddings is None or not self.passages:
            return []
        embed_model = self._get_embed_model()
        if embed_model is None:
            return []
        q_raw = list(embed_model.embed([query]))[0]
        q_vec = np.array(q_raw, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec /= q_norm

        sims = np.dot(self.embeddings, q_vec)
        top_indices = np.argsort(sims)[::-1][:top_k]
        return [(int(idx), float(sims[idx])) for idx in top_indices]

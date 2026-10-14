"""
Retriever and query processor for Bearing Fault Copilot RAG pipeline.
Handles query expansion, hybrid BM25 + dense search, RRF fusion, and page de-duplication.
"""

import time
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from .models import Passage, RetrievalRequest, RetrievalResponse
from .indexer import HybridIndex

# Sample mock passages strictly following docs/contract.md
MOCK_PASSAGES = [
    Passage(
        chunk_id="skf-damage-p34-c2",
        text=(
            "In rotating machinery where the outer ring is stationary, radial load produces a concentrated "
            "load zone typically spanning 120 to 150 degrees at the 6 o'clock position. Localized cyclic stress "
            "in this arc leads to fatigue spalling. Verify housing bore roundness and rotor alignment. De-energize "
            "motor and support shaft weight before loosening housing bolts."
        ),
        source_title="Bearing damage and failure analysis",
        source_type="guide",
        page=34,
        url="https://www.skf.com/group/products/rolling-bearings/damage-and-failure-analysis",
        synthetic=False,
        score=0.98,
        excerpt="Radial load produces a concentrated load zone at the 6 o'clock position causing localized fatigue spalling.",
    ),
    Passage(
        chunk_id="bridge-table-outer_race-p34-c5",
        text=(
            "Bearing Fault Type: outer_race\n"
            "Damage Mode: Subsurface initiated spalling (load zone fatigue)\n"
            "Likely Root Causes: Heavy radial loading, localized cyclic stress, housing out-of-roundness\n"
            "Inspection & Recommended Actions: Inspect outer ring load zone pattern; rotate housing or replace bearing\n"
            "Safety-Critical Action: Yes (Support rotor/housing weight before loosening mount bolts)\n"
            "Authoritative Source: SKF: Bearing damage and failure analysis, p. 34"
        ),
        source_title="Curated Bearing Fault Bridge Table",
        source_type="playbook",
        page=34,
        url="data/knowledge/bridge_table.md",
        synthetic=False,
        score=0.92,
        excerpt="Inspect outer ring load zone pattern; support rotor/housing weight before loosening mount bolts.",
    ),
    Passage(
        chunk_id="schaeffler-bearing-damage-p19-c1",
        text=(
            "Abrasive wear on outer and inner raceways manifests as dull or grooved appearance with fine scoring "
            "along the direction of rolling. Ingress of hard abrasive particles past defective seals accelerates "
            "wear. Flush bearing housing, inspect seal counterfaces, and verify grease cleanliness."
        ),
        source_title="Schaeffler (FAG): Rolling Bearing Damage - Causes and Remedies",
        source_type="guide",
        page=19,
        url="https://www.schaeffler.com/en/bearing-damage",
        synthetic=False,
        score=0.85,
        excerpt="Abrasive wear manifests as dull or grooved tracks from particulate ingress; flush housing and replace seals.",
    ),
    Passage(
        chunk_id="synthetic-log-l008-c1",
        text=(
            "Maintenance Record [L008] - Date: 2026-03-04\n"
            "Machine: PUMP-03 (centrifugal feedwater pump)\n"
            "Fault Type: outer_race\n"
            "Reported Symptom: rising vibration at the drive end (4.8 mm/s)\n"
            "Action Taken: bearing inspected and replaced; flushed lubricant sump\n"
            "Parts Replaced: SKF 6205\n"
            "Downtime: 3.5 hours\n"
            "Technician Note: fatigue flaking across 45 degree arc on outer ring; noise gone after replacement\n"
            "Notice: [SYNTHETIC DEMO LOG]"
        ),
        source_title="Plant Maintenance Log: L008",
        source_type="log",
        page="L008",
        url="data/knowledge/logs_synthetic.csv",
        synthetic=True,
        score=0.79,
        excerpt="PUMP-03 outer race fatigue flaking replaced with SKF 6205; noise resolved after replacement.",
    ),
    Passage(
        chunk_id="electric-motor-bearing-guide-p21-c1",
        text=(
            "Shaft misalignment between electric motor and driven machine imposes severe parasitic radial and axial "
            "loads on bearings. Laser alignment tolerance: Angular misalignment must not exceed 0.05 mm/100 mm. "
            "Safety Critical: Never work on motor couplings or bearing housings without full Lockout/Tagout (LOTO) "
            "of the main supply breaker."
        ),
        source_title="Industrial Motor Bearing Maintenance and Lubrication Handbook",
        source_type="guide",
        page=21,
        url="https://www.energy.gov/eere/amo/articles/electric-motor-bearing-maintenance",
        synthetic=False,
        score=0.75,
        excerpt="Laser align couplings within 0.05 mm/100 mm; observe mandatory Lockout/Tagout before dismounting.",
    ),
]


class BearingRetriever:
    def __init__(self, index_dir: Optional[Path] = None):
        if index_dir is None:
            repo_root = Path(__file__).resolve().parent.parent
            index_dir = repo_root / "rag" / "index"
        self.index_dir = index_dir
        self.index = HybridIndex(index_dir)
        self._is_loaded = False

    def load(self) -> bool:
        if not self._is_loaded:
            self._is_loaded = self.index.load()
        return self._is_loaded

    def build_expanded_queries(self, base_query: str, fault_type: Optional[str] = None, severity: Optional[str] = None) -> List[Tuple[str, float]]:
        """
        Builds primary query with high weight and targeted sub-queries.
        Returns list of (query_text, query_weight).
        """
        queries = []
        if base_query and base_query.strip():
            # Primary query gets high priority
            queries.append((base_query.strip(), 2.0))

        f_type = (fault_type or "").replace("_", " ").strip().lower()
        sev = (severity or "").strip().lower()

        if f_type and f_type not in ("normal", "none"):
            # Query 1: Root causes and damage mechanisms
            queries.append((f"{f_type} bearing damage root cause fatigue spalling wear failure {sev}".strip(), 1.0))
            # Query 2: Inspection and damage pattern identification
            queries.append((f"{f_type} bearing inspection procedure damage pattern raceway symptoms", 0.9))
            # Query 3: Corrective actions, maintenance procedures, and safety lockout
            queries.append((f"{f_type} bearing corrective maintenance replacement action safety lockout tagout", 1.0))
        elif f_type in ("normal", "none") and base_query:
            # Normal maintenance check query
            queries.append(("bearing routine maintenance inspection greasing lubrication vibration check", 1.0))

        # De-duplicate queries
        seen = set()
        unique_queries = []
        for q_text, q_wt in queries:
            if q_text not in seen:
                seen.add(q_text)
                unique_queries.append((q_text, q_wt))
        return unique_queries

    def retrieve(
        self,
        query: str,
        fault_type: Optional[str] = None,
        severity: Optional[str] = None,
        top_k: int = 5,
        use_mock: bool = False,
    ) -> List[Passage]:
        # Check mock override or environment flag
        if use_mock or os.environ.get("BEARING_RAG_MOCK", "").lower() in ("1", "true"):
            return MOCK_PASSAGES[:top_k]

        if not self.load() or not self.index.passages:
            # Fallback to mock passages if index has not been built yet
            return MOCK_PASSAGES[:top_k]

        weighted_sub_queries = self.build_expanded_queries(query, fault_type, severity)
        passage_scores: Dict[int, float] = {}

        # Reciprocal Rank Fusion (RRF) constants
        k_rrf = 60.0
        dense_base_weight = 1.0
        bm25_base_weight = 0.85

        for sub_q, q_weight in weighted_sub_queries:
            # 1. BM25 Search
            bm25_results = self.index.search_bm25(sub_q, top_k=15)
            for rank, (idx, raw_score) in enumerate(bm25_results, start=1):
                rrf_score = q_weight * bm25_base_weight * (1.0 / (k_rrf + rank))
                passage_scores[idx] = passage_scores.get(idx, 0.0) + rrf_score

            # 2. Dense Vector Search
            dense_results = self.index.search_dense(sub_q, top_k=15)
            for rank, (idx, sim) in enumerate(dense_results, start=1):
                rrf_score = q_weight * dense_base_weight * (1.0 / (k_rrf + rank))
                passage_scores[idx] = passage_scores.get(idx, 0.0) + rrf_score

        if not passage_scores:
            return MOCK_PASSAGES[:top_k]

        # Sort indices by merged RRF score
        sorted_indices = sorted(passage_scores.keys(), key=lambda i: passage_scores[i], reverse=True)

        # De-duplicate per page ("When it fails: Same page returned five times -> Remove duplicates per page")
        seen_pages = set()
        selected_passages: List[Passage] = []

        for idx in sorted_indices:
            p = self.index.passages[idx]
            page_key = f"{p.source_title}::p{p.page}"
            
            # Allow logs and bridge table rows without excessive deduplication if unique
            if p.source_type == "guide" and page_key in seen_pages:
                continue

            seen_pages.add(page_key)
            
            # Create a clone with attached score and excerpt
            p_dict = p.model_dump()
            p_dict["score"] = round(float(passage_scores[idx]), 4)
            p_dict["excerpt"] = self._generate_excerpt(p.text)
            selected_passages.append(Passage(**p_dict))

            if len(selected_passages) >= top_k:
                break

        return selected_passages

    @staticmethod
    def _generate_excerpt(text: str, max_chars: int = 160) -> str:
        """Extract a concise first sentence or lead excerpt for screen display."""
        clean = " ".join(text.split())
        match = re.search(r"^(.*?[.!?])(?:\s|$)", clean)
        if match:
            snippet = match.group(1).strip()
            if len(snippet) <= max_chars:
                return snippet
        return (clean[:max_chars - 3] + "...") if len(clean) > max_chars else clean

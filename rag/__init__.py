"""
RAG Pipeline package for Bearing Fault Copilot.
Owner: Santos
"""

from .interface import retrieve, format_passages_for_prompt, Passage, RetrievalRequest, RetrievalResponse

__all__ = [
    "retrieve",
    "format_passages_for_prompt",
    "Passage",
    "RetrievalRequest",
    "RetrievalResponse",
]

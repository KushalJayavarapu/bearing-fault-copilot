"""
Data models for the RAG pipeline adhering to docs/contract.md.
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class Passage(BaseModel):
    chunk_id: str = Field(..., description="Stable unique ID, e.g., skf-damage-p34-c1")
    text: str = Field(..., description="Chunk textual content")
    source_title: str = Field(..., description="Title of the source guide or document")
    source_type: str = Field(..., description="'guide', 'playbook', or 'log'")
    page: Union[int, str] = Field(..., description="Page number or section label")
    url: str = Field(..., description="URL or source reference")
    synthetic: Optional[bool] = Field(default=None, description="Flagged true for synthetic maintenance logs")
    score: Optional[float] = Field(default=None, description="Retrieval score for internal ranking")
    excerpt: Optional[str] = Field(default=None, description="Short snippet for UI citations")


class RetrievalRequest(BaseModel):
    query: str
    fault_type: Optional[str] = None
    severity: Optional[str] = None
    top_k: int = 5


class RetrievalResponse(BaseModel):
    passages: List[Passage]

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)

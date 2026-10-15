"""
Main interface for Bearing Fault Copilot RAG pipeline.
Called by Kushal's orchestrator service adhering strictly to docs/contract.md.
"""

from typing import Union, Dict, Any, Optional, List
from .models import Passage, RetrievalRequest, RetrievalResponse
from .retriever import BearingRetriever
from .prompt_helper import format_passages_for_prompt, construct_rag_prompt, SYSTEM_PROMPT_TEMPLATE

_DEFAULT_RETRIEVER: Optional[BearingRetriever] = None


def get_retriever() -> BearingRetriever:
    global _DEFAULT_RETRIEVER
    if _DEFAULT_RETRIEVER is None:
        _DEFAULT_RETRIEVER = BearingRetriever()
    return _DEFAULT_RETRIEVER


def retrieve(
    query: Optional[str] = None,
    fault_type: Optional[str] = None,
    severity: Optional[str] = None,
    top_k: int = 5,
    use_mock: bool = False,
    request: Optional[Union[Dict[str, Any], RetrievalRequest]] = None,
) -> Dict[str, Any]:
    """
    Primary RAG function adhering to docs/contract.md.
    
    Can be called either with keyword arguments or with a dictionary/RetrievalRequest:
        retrieve("outer race defect, small...", fault_type="outer_race", severity="small", top_k=5)
        or
        retrieve(request={"query": "...", "fault_type": "outer_race", "severity": "small", "top_k": 5})

    Returns:
        {"passages": [{"chunk_id": "...", "text": "...", "source_title": "...", "source_type": "...", "page": 34, "url": "..."}]}
    """
    if request is not None:
        if isinstance(request, dict):
            req_obj = RetrievalRequest(**request)
        else:
            req_obj = request
        q = req_obj.query
        f_type = req_obj.fault_type
        sev = req_obj.severity
        k = req_obj.top_k
    else:
        q = query or ""
        f_type = fault_type
        sev = severity
        k = top_k

    retriever = get_retriever()
    passages: List[Passage] = retriever.retrieve(
        query=q,
        fault_type=f_type,
        severity=sev,
        top_k=k,
        use_mock=use_mock,
    )

    # Return pure contract dictionary
    formatted_passages = []
    for p in passages:
        p_dict = {
            "chunk_id": p.chunk_id,
            "text": p.text,
            "source_title": p.source_title,
            "source_type": p.source_type,
            "page": p.page,
            "url": p.url,
        }
        if p.synthetic:
            p_dict["synthetic"] = True
        if p.excerpt:
            p_dict["excerpt"] = p.excerpt
        formatted_passages.append(p_dict)

    return {"passages": formatted_passages}

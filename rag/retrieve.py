"""
Direct entrypoint for orchestrator retrieval:
    from rag.retrieve import retrieve

Adheres strictly to docs/contract.md section 2.
"""

from typing import Union, Dict, Any, Optional
from .interface import retrieve as _retrieve


def retrieve(
    request: Optional[Union[Dict[str, Any], str]] = None,
    query: Optional[str] = None,
    fault_type: Optional[str] = None,
    severity: Optional[str] = None,
    top_k: int = 5,
    use_mock: bool = False,
) -> Dict[str, Any]:
    """
    Main retrieval function for orchestrator integration.
    
    Accepts:
        1. A request dictionary strictly matching docs/contract.md:
           retrieve({
               "query": "outer race defect, small, deep groove ball bearing: causes and actions",
               "fault_type": "outer_race",
               "severity": "small",
               "top_k": 5
           })
        2. Keyword arguments:
           retrieve("outer race defect...", fault_type="outer_race", severity="small", top_k=5)
        3. Mock mode:
           retrieve({"use_mock": True, ...}) or retrieve(use_mock=True)

    Returns:
        {
            "passages": [
                {
                    "chunk_id": "skf-damage-p34-c2",
                    "text": "...",
                    "source_title": "Bearing damage and failure analysis",
                    "source_type": "guide",
                    "page": 34,
                    "url": "https://..."
                }
            ]
        }
    """
    if isinstance(request, dict):
        q = request.get("query", "")
        ft = request.get("fault_type")
        sev = request.get("severity")
        k = request.get("top_k", 5)
        mock = request.get("mock", False) or request.get("use_mock", False) or use_mock
        return _retrieve(query=q, fault_type=ft, severity=sev, top_k=k, use_mock=mock)
    elif isinstance(request, str):
        return _retrieve(query=request, fault_type=fault_type, severity=severity, top_k=top_k, use_mock=use_mock)
    else:
        return _retrieve(query=query, fault_type=fault_type, severity=severity, top_k=top_k, use_mock=use_mock)


__all__ = ["retrieve"]

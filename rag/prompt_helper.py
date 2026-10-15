"""
Prompt formatting helper for Kushal's LLM pipeline.
Enforces strict anti-hallucination rules and formats retrieved passages with chunk IDs.
"""

from typing import List
from .models import Passage

SYSTEM_PROMPT_TEMPLATE = """You are an expert industrial reliability engineer assistant analyzing bearing faults.
You explain detected bearing faults, likely causes, and recommended actions based strictly on the retrieved technical documentation and plant maintenance history provided below.

Strict Compliance Rules:
1. Answer ONLY using the facts present in the retrieved passages. Do NOT extrapolate or assume unstated facts.
2. Every claim, likely cause, and recommended action MUST cite one or more [chunk_id] sources in brackets (e.g., [skf-damage-p34-c2]).
3. If the retrieved passages do NOT cover an aspect, explicitly state: "The provided documentation does not specify [aspect]."
4. NEVER invent a citation, guide title, or chunk ID. Only cite chunk IDs from the numbered list below.
5. If an action involves electrical isolation, heavy rigging, or Lockout/Tagout (LOTO), explicitly flag it as safety_critical.
"""


def format_passages_for_prompt(passages: List[Passage]) -> str:
    """
    Formats retrieved passages into a structured reference text for injection into the LLM prompt.
    Includes chunk_id, source title, page number, and source type.
    """
    if not passages:
        return "No passages retrieved."

    lines = ["### Retrieved Reference Documentation:\n"]
    for i, p in enumerate(passages, start=1):
        lines.append(f"[{i}] Chunk ID: {p.chunk_id}")
        lines.append(f"    Source: {p.source_title} (Page/Section: {p.page}, Type: {p.source_type})")
        if p.synthetic:
            lines.append("    Notice: [SYNTHETIC MAINTENANCE RECORD]")
        lines.append(f"    Passage Text:\n    \"{p.text}\"\n")

    return "\n".join(lines)


def construct_rag_prompt(
    sensor_summary: str,
    passages: List[Passage],
    fault_type: str,
    severity: str,
) -> str:
    """
    Constructs the complete user prompt for the LLM.
    """
    passages_text = format_passages_for_prompt(passages)
    
    prompt = f"""Fault Diagnostic Report:
- Detected Fault: {fault_type}
- Severity: {severity}
- Sensor Context: {sensor_summary}

{passages_text}

Instructions:
1. Provide a plain-language explanation of the diagnosed defect.
2. List likely physical root causes citing specific chunk IDs.
3. Recommend actionable maintenance steps (including inspection, replacement, lubrication, and alignment), citing specific chunk IDs.
4. Mark any safety-critical steps (e.g., lockout/tagout, rotor rigging) clearly.
5. State any uncertainty if documentation lacks specific details.
"""
    return prompt

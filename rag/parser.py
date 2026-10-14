"""
Parser and Chunker for Bearing Fault Copilot knowledge documents.
Extracts page-by-page text from guides, bridge table, and synthetic logs.
"""

import csv
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from .models import Passage


def parse_page_markers(text: str) -> List[Tuple[int, str]]:
    """
    Splits text on [[page X]] markers and returns list of (page_num, page_text).
    """
    pattern = re.compile(r'\[\[page\s+(\d+)\]\]', re.IGNORECASE)
    splits = pattern.split(text)
    pages = []
    
    # If text starts before first marker
    if splits and splits[0].strip():
        initial_text = splits[0].strip()
        pages.append((1, initial_text))
        remaining = splits[1:]
    else:
        remaining = splits[1:] if splits else []

    for i in range(0, len(remaining), 2):
        if i + 1 < len(remaining):
            page_num = int(remaining[i])
            page_content = remaining[i + 1].strip()
            pages.append((page_num, page_content))
            
    return pages


def chunk_text(text: str, target_words: int = 250, overlap_words: int = 40) -> List[str]:
    """
    Splits text into chunks of target_words with overlap, respecting paragraph / sentence boundaries.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()] if text.strip() else []

    chunks = []
    current_words = []

    for para in paragraphs:
        para_words = para.split()
        if not para_words:
            continue
        
        # If adding this paragraph exceeds target words and we already have content
        if len(current_words) + len(para_words) > target_words and current_words:
            chunk_str = " ".join(current_words)
            chunks.append(chunk_str)
            # Retain overlap from end of current chunk
            overlap = current_words[-overlap_words:] if len(current_words) > overlap_words else current_words
            current_words = list(overlap)

        # If a single paragraph is larger than target_words, split by sentences
        if len(para_words) > target_words:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
                sent_words = sentence.split()
                if not sent_words:
                    continue
                if len(current_words) + len(sent_words) > target_words and current_words:
                    chunks.append(" ".join(current_words))
                    overlap = current_words[-overlap_words:] if len(current_words) > overlap_words else current_words
                    current_words = list(overlap)
                current_words.extend(sent_words)
        else:
            current_words.extend(para_words)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def load_manifest(manifest_path: Path) -> Dict[str, Dict[str, Any]]:
    if not manifest_path.exists():
        return {}
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {item["slug"]: item for item in data}


def ingest_guides(guides_dir: Path, manifest: Dict[str, Dict[str, Any]]) -> List[Passage]:
    passages = []
    if not guides_dir.exists():
        return passages

    for guide_file in sorted(guides_dir.glob("*.txt")):
        slug = guide_file.stem
        meta = manifest.get(slug, {
            "source_title": slug.replace("-", " ").title(),
            "url": f"https://bearing-guides.local/{slug}",
            "slug": slug,
        })
        
        raw_text = guide_file.read_text(encoding="utf-8")
        pages = parse_page_markers(raw_text)
        
        for page_num, page_text in pages:
            if not page_text.strip():
                continue
            chunks = chunk_text(page_text, target_words=220, overlap_words=35)
            for c_idx, chunk_content in enumerate(chunks, start=1):
                chunk_id = f"{slug}-p{page_num}-c{c_idx}"
                passages.append(
                    Passage(
                        chunk_id=chunk_id,
                        text=chunk_content,
                        source_title=meta.get("source_title", slug),
                        source_type="guide",
                        page=page_num,
                        url=meta.get("url", ""),
                        synthetic=False,
                    )
                )

    return passages


def ingest_bridge_table(bridge_path: Path) -> List[Passage]:
    passages = []
    if not bridge_path.exists():
        return passages

    content = bridge_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    # Extract markdown table rows
    table_rows = []
    in_table = False
    for line in lines:
        if line.startswith("|") and ("Fault type" in line or "Damage mode" in line):
            in_table = True
            continue
        if in_table and line.startswith("| :---"):
            continue
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 6:
                table_rows.append(parts)
        elif in_table and not line.startswith("|"):
            in_table = False

    for idx, row in enumerate(table_rows, start=1):
        fault_type = row[0].replace("`", "").strip()
        damage_mode = row[1].strip()
        likely_causes = row[2].strip()
        actions = row[3].strip()
        safety_critical = row[4].strip()
        source_page = row[5].strip()

        # Extract page number if present
        page_match = re.search(r'p\.\s*(\d+)', source_page, re.IGNORECASE)
        page_val = int(page_match.group(1)) if page_match else "bridge-table"

        text_block = (
            f"Bearing Fault Type: {fault_type}\n"
            f"Damage Mode: {damage_mode}\n"
            f"Likely Root Causes: {likely_causes}\n"
            f"Inspection & Recommended Actions: {actions}\n"
            f"Safety-Critical Action: {safety_critical}\n"
            f"Authoritative Source: {source_page}"
        )

        chunk_id = f"bridge-table-{fault_type}-p{page_val}-c{idx}"
        passages.append(
            Passage(
                chunk_id=chunk_id,
                text=text_block,
                source_title="Curated Bearing Fault Bridge Table",
                source_type="playbook",
                page=page_val,
                url="data/knowledge/bridge_table.md",
                synthetic=False,
            )
        )

    return passages


def ingest_synthetic_logs(logs_path: Path) -> List[Passage]:
    passages = []
    if not logs_path.exists():
        return passages

    with open(logs_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            entry_id = row.get("entry_id", f"L{idx:03d}")
            machine = f"{row.get('machine_id', '')} ({row.get('machine_type', '')})"
            text_block = (
                f"Maintenance Record [{entry_id}] - Date: {row.get('date', '')}\n"
                f"Machine: {machine}\n"
                f"Fault Type: {row.get('fault_type', '')}\n"
                f"Reported Symptom: {row.get('symptom', '')}\n"
                f"Action Taken: {row.get('action_taken', '')}\n"
                f"Parts Replaced: {row.get('parts_replaced', '')}\n"
                f"Downtime: {row.get('downtime_hours', '')} hours\n"
                f"Technician Note: {row.get('technician_note', '')}\n"
                f"Notice: [SYNTHETIC DEMO LOG]"
            )
            chunk_id = f"synthetic-log-{entry_id.lower()}-c1"
            passages.append(
                Passage(
                    chunk_id=chunk_id,
                    text=text_block,
                    source_title=f"Plant Maintenance Log: {entry_id}",
                    source_type="log",
                    page=entry_id,
                    url="data/knowledge/logs_synthetic.csv",
                    synthetic=True,
                )
            )

    return passages


def ingest_all_documents(repo_root: Path) -> List[Passage]:
    data_dir = repo_root / "data"
    manifest_path = data_dir / "manifest.json"
    manifest = load_manifest(manifest_path)

    all_passages: List[Passage] = []

    # 1. Guides
    guides_dir = data_dir / "guides"
    guide_passages = ingest_guides(guides_dir, manifest)
    all_passages.extend(guide_passages)

    # 2. Bridge table
    bridge_path = data_dir / "knowledge" / "bridge_table.md"
    bridge_passages = ingest_bridge_table(bridge_path)
    all_passages.extend(bridge_passages)

    # 3. Synthetic logs
    logs_path = data_dir / "knowledge" / "logs_synthetic.csv"
    log_passages = ingest_synthetic_logs(logs_path)
    all_passages.extend(log_passages)

    return all_passages

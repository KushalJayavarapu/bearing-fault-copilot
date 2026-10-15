"""
One-command script to rebuild the RAG search index from data/ sources.
Usage:
    python -m rag.build_index
"""

import sys
from pathlib import Path
from .parser import ingest_all_documents
from .indexer import HybridIndex


def main():
    repo_root = Path(__file__).resolve().parent.parent
    index_dir = repo_root / "rag" / "index"

    print("=" * 60)
    print("Bearing Fault Copilot - Building RAG Search Index")
    print("=" * 60)

    passages = ingest_all_documents(repo_root)
    if not passages:
        print("ERROR: No passages found to index. Check data/ directory.")
        return 1

    print(f"Total passages parsed: {len(passages)}")
    types = {}
    for p in passages:
        types[p.source_type] = types.get(p.source_type, 0) + 1
    for stype, count in types.items():
        print(f"  - {stype}: {count} passages")

    hybrid_index = HybridIndex(index_dir)
    hybrid_index.build(passages)
    hybrid_index.save()

    print("Index build complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

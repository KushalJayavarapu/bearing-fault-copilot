"""
Build script entrypoint for RAG index.
Usage:
    python -m rag.build
"""

import sys
from .build_index import main

if __name__ == "__main__":
    sys.exit(main())

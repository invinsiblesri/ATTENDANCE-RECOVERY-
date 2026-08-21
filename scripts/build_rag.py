"""
RAG Vector Store Builder Script.
Ingests markdown documents from rag/documents/ into the ChromaDB vector database.
"""

import os
import sys

# Ensure backend root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from rag.vector_store import get_policy_vector_store


def main():
    print("=" * 60)
    print("AI Attendance Recovery Agent - ChromaDB RAG Indexer")
    print("=" * 60)

    store = get_policy_vector_store()
    print(f"Reading documents from: {store.docs_dir}")
    print(f"ChromaDB persistence:  {store.persist_dir}")

    total_chunks = store.build_index()
    print(f"\nIndexing complete! Indexed {total_chunks} policy chunks into ChromaDB.")
    print("=" * 60)


if __name__ == "__main__":
    main()

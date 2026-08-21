"""
RAG Service for College Attendance Policies.
Exposes search_attendance_policy(query: str, n_results: int = 3).
"""

from typing import List, Dict, Any, Optional
from .vector_store import get_policy_vector_store, PolicyVectorStore


def search_attendance_policy(
    query: str,
    n_results: int = 3,
    vector_store: Optional[PolicyVectorStore] = None
) -> List[Dict[str, Any]]:
    """
    Searches the demo attendance policy knowledge base for relevant policy chunks.

    Args:
        query: Search query (e.g. "What is the minimum overall attendance required?")
        n_results: Number of top relevant policy chunks to return (default 3)
        vector_store: Optional custom PolicyVectorStore instance

    Returns:
        List of matching policy records with content, source, section, and similarity_score.
    """
    store = vector_store or get_policy_vector_store()
    return store.search(query=query, n_results=n_results)

"""
Unit and Integration Tests for ChromaDB RAG Knowledge Base.
Verifies:
- Document indexing of prototype policy files
- Policy documents strictly labelled 'Demo College Attendance Policy — Hackathon Prototype'
- Semantic search query retrieval
- Zero external API key dependencies
"""

import unittest
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from rag.vector_store import PolicyVectorStore, get_policy_vector_store
from rag.service import search_attendance_policy


class TestRAGRetrieval(unittest.TestCase):
    """Tests for local ChromaDB attendance policy search."""

    @classmethod
    def setUpClass(cls):
        cls.store = get_policy_vector_store()
        cls.store.build_index()

    def test_collection_contains_chunks(self):
        """Verify policy documents were indexed into ChromaDB."""
        self.assertGreater(self.store.collection.count(), 0)

    def test_minimum_attendance_query(self):
        """Verify search for minimum attendance policy."""
        results = search_attendance_policy("What is the minimum overall attendance required?", n_results=2)
        self.assertGreaterEqual(len(results), 1)

        # Check content contains 80% rule
        top = results[0]
        self.assertIn("80", top["content"])
        self.assertTrue("Demo College Attendance Policy" in top["title"] or "Demo College Attendance Policy" in top["content"])

    def test_exam_eligibility_query(self):
        """Verify search for examination eligibility policy."""
        results = search_attendance_policy("What are the examination eligibility criteria?", n_results=2)
        self.assertGreaterEqual(len(results), 1)

        # Should retrieve from exam_eligibility.md
        sources = [r["source"] for r in results]
        self.assertIn("exam_eligibility.md", sources)

    def test_attendance_recovery_query(self):
        """Verify search for attendance recovery roadmap."""
        results = search_attendance_policy("How can a student recover shortage attendance?", n_results=2)
        self.assertGreaterEqual(len(results), 1)

        sources = [r["source"] for r in results]
        self.assertIn("attendance_recovery.md", sources)

    def test_no_invented_regulations_in_retrieval(self):
        """
        Verify that retrieved chunks do NOT contain invented regulations
        (no condonation brackets, detention rules, official medical exemptions, etc.).
        """
        results = search_attendance_policy("condonation detention medical exemption", n_results=3)
        for r in results:
            content_lower = r["content"].lower()
            self.assertNotIn("condonation", content_lower)
            self.assertNotIn("detention", content_lower)
            self.assertNotIn("hall-ticket fee", content_lower)


if __name__ == "__main__":
    unittest.main()

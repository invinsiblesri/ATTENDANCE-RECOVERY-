"""
Local ChromaDB Vector Store for College Attendance Policies.
Indexes prototype policy documents strictly labelled 'Demo College Attendance Policy — Hackathon Prototype'.
Operates 100% locally with zero external API key requirements.
"""

import os
import shutil
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

import chromadb
from chromadb.config import Settings
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

os.environ["ANONYMIZED_TELEMETRY"] = "False"

DEFAULT_DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
DEFAULT_CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "chroma_db")
COLLECTION_NAME = "college_attendance_policies"
VECTOR_DIMENSION = 256


class LocalPolicyEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    Local, deterministic, fixed-dimension vector embedding function for ChromaDB.
    Guarantees 100% offline execution without downloading models or requiring API keys.
    """

    def __init__(self, n_features: int = VECTOR_DIMENSION):
        self.n_features = n_features
        self.vectorizer = HashingVectorizer(
            n_features=n_features,
            ngram_range=(1, 2),
            norm="l2",
            alternate_sign=False
        )

    def __call__(self, input: Documents) -> Embeddings:
        matrix = self.vectorizer.transform(input).toarray().astype(np.float32)
        return matrix.tolist()


class PolicyVectorStore:
    """Manages indexing and retrieval of attendance policy documents using ChromaDB."""

    def __init__(self, persist_dir: Optional[str] = None, docs_dir: Optional[str] = None):
        self.persist_dir = persist_dir or DEFAULT_CHROMA_DIR
        self.docs_dir = docs_dir or DEFAULT_DOCS_DIR
        os.makedirs(self.persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        self.embedding_fn = LocalPolicyEmbeddingFunction(n_features=VECTOR_DIMENSION)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn
        )

    def _chunk_document(self, content: str, source_filename: str) -> List[Dict[str, Any]]:
        """
        Chunks markdown document by headers (## ) while preserving context.
        """
        chunks = []
        doc_title = "Demo College Attendance Policy — Hackathon Prototype"
        lines = content.strip().split("\n")

        current_section = "General Overview"
        current_buffer = []

        for line in lines:
            if line.startswith("# "):
                doc_title = line.replace("# ", "").strip()
            elif line.startswith("## "):
                if current_buffer:
                    chunk_text = "\n".join(current_buffer).strip()
                    if chunk_text:
                        chunks.append({
                            "text": f"[{doc_title}] {current_section}\n{chunk_text}",
                            "source": source_filename,
                            "title": doc_title,
                            "section": current_section
                        })
                    current_buffer = []
                current_section = line.replace("## ", "").strip()
            else:
                if line.strip():
                    current_buffer.append(line.strip())

        if current_buffer:
            chunk_text = "\n".join(current_buffer).strip()
            if chunk_text:
                chunks.append({
                    "text": f"[{doc_title}] {current_section}\n{chunk_text}",
                    "source": source_filename,
                    "title": doc_title,
                    "section": current_section
                })

        return chunks

    def build_index(self) -> int:
        """
        Reads all markdown documents from docs_dir, chunks them, and stores them in ChromaDB.
        Returns total number of chunks indexed.
        """
        if not os.path.exists(self.docs_dir):
            raise FileNotFoundError(f"Documents directory '{self.docs_dir}' does not exist.")

        all_chunks = []
        for fname in sorted(os.listdir(self.docs_dir)):
            if fname.endswith(".md") or fname.endswith(".txt"):
                fpath = os.path.join(self.docs_dir, fname)
                with open(fpath, "r", encoding="utf-8") as fp:
                    content = fp.read()
                chunks = self._chunk_document(content, fname)
                all_chunks.extend(chunks)

        if not all_chunks:
            return 0

        ids = [f"chunk_{i:04d}_{c['source'].replace('.', '_')}" for i, c in enumerate(all_chunks)]
        docs = [c["text"] for c in all_chunks]
        metadatas = [
            {
                "source": c["source"],
                "title": c["title"],
                "section": c["section"]
            }
            for c in all_chunks
        ]

        self.collection.upsert(
            ids=ids,
            documents=docs,
            metadatas=metadatas
        )

        return len(all_chunks)

    def search(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Searches the ChromaDB collection for the most relevant policy documents.
        """
        if self.collection.count() == 0:
            self.build_index()

        results = self.collection.query(
            query_texts=[query],
            n_results=min(n_results, max(1, self.collection.count()))
        )

        formatted = []
        if results and results.get("documents") and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

            for doc_text, meta, dist in zip(docs, metas, distances):
                formatted.append({
                    "content": doc_text,
                    "source": meta.get("source", "Unknown"),
                    "title": meta.get("title", "Demo College Attendance Policy"),
                    "section": meta.get("section", "Policy Section"),
                    "similarity_score": round(max(0.0, 1.0 - float(dist)), 4) if dist is not None else 1.0,
                    "metadata": meta
                })

        return formatted


# Singleton instance
_vector_store_instance: Optional[PolicyVectorStore] = None


def get_policy_vector_store(persist_dir: Optional[str] = None, docs_dir: Optional[str] = None) -> PolicyVectorStore:
    """Returns the singleton PolicyVectorStore instance."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = PolicyVectorStore(persist_dir=persist_dir, docs_dir=docs_dir)
    return _vector_store_instance

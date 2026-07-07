from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import chromadb


class SearchResultChunk(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any]
    similarity_score: Optional[float] = None


class BaseVectorStore(ABC):
    @abstractmethod
    def add(self, ids: List[str], embeddings: List[List[float]],
            documents: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """Adds vectorized documents with explicit embeddings and uniform string IDs."""
        pass

    @abstractmethod
    def query(self, query_embedding: List[float], top_k: int,
              document_id: Optional[str] = None) -> List[SearchResultChunk]:
        """Queries the store and returns a normalized, backend-agnostic schema."""
        pass


class ChromaVectorStore(BaseVectorStore):
    def __init__(self, path: str = "./chromadb_store"):
        self.client = chromadb.PersistentClient(path=path)
        # Distance space is fixed at creation time and can't change afterward.
        # If a collection named "excerpta_documents" already exists on disk
        # from earlier testing, get_or_create_collection() returns it as-is
        # and silently ignores this config — delete ./chromadb_store once
        # before your first real ingestion run.
        self.collection = self.client.get_or_create_collection(
            name="excerpta_documents",
            configuration={"hnsw": {"space": "cosine"}},
        )

    def add(self, ids, embeddings, documents, metadatas) -> None:
        self.collection.upsert(ids=ids, embeddings=embeddings,
                                documents=documents, metadatas=metadatas)

    def query(self, query_embedding, top_k, document_id=None) -> List[SearchResultChunk]:
        where_clause = {"document_id": document_id} if document_id else None
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=top_k, where=where_clause,
        )
        if not results["ids"] or not results["ids"][0]:
            return []
        return [
            SearchResultChunk(
                id=results["ids"][0][i],
                text=results["documents"][0][i],
                metadata=results["metadatas"][0][i],
                similarity_score=1.0 - results["distances"][0][i],
            )
            for i in range(len(results["ids"][0]))
        ]


vector_store: BaseVectorStore = ChromaVectorStore()

# Lazy singleton: loaded on first actual use, not at import time. Loading
# eagerly at module level fixed the original "reload every call" latency
# bug, but it meant merely *importing* this module — which api/main.py does
# — pulled a 567M-parameter model off HuggingFace, even for tests that never
# call embed_chunks() at all. This gets both: loaded once, and only when
# something actually needs it.
_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("BAAI/bge-m3", device="cpu")
    return _embedding_model


def embed_chunks(texts: List[str]) -> List[List[float]]:
    return _get_embedding_model().encode(texts, normalize_embeddings=True).tolist()
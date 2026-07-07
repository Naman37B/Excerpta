import pickle
from pathlib import Path
from rank_bm25 import BM25Okapi
from services.embeddings import vector_store

BM25_PATH = Path("./bm25_index.pkl")


class BM25Index:
    def __init__(self):
        self.ids, self.texts, self.metadatas, self.bm25 = [], [], [], None
        if BM25_PATH.exists():
            self.ids, self.texts, self.metadatas = pickle.load(open(BM25_PATH, "rb"))
            self._build()

    def _build(self):
        self.bm25 = BM25Okapi([t.lower().split() for t in self.texts]) if self.texts else None

    def add_document(self, new_ids: list[str], new_texts: list[str], new_metadatas: list[dict]):
        self.ids += new_ids
        self.texts += new_texts
        self.metadatas += new_metadatas
        self._build()
        pickle.dump((self.ids, self.texts, self.metadatas), open(BM25_PATH, "wb"))

    def search(self, query: str, top_k: int, document_id: str | None = None) -> list[dict]:
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(query.lower().split())
        # Filter to the scoped document BEFORE truncating to top_k, not after —
        # filtering post-truncation can silently return fewer than top_k results.
        valid = [i for i in range(len(scores))
                 if not document_id or self.metadatas[i].get("document_id") == document_id]
        top = sorted(valid, key=lambda i: scores[i], reverse=True)[:top_k]
        return [{"id": self.ids[i], "text": self.texts[i], "metadata": self.metadatas[i]} for i in top]


bm25_index = BM25Index()


def reciprocal_rank_fusion(dense: list[dict], sparse: list[dict], k: int = 60) -> list[dict]:
    scores, chunks = {}, {}
    for rank, item in enumerate(dense):
        scores[item["id"]] = scores.get(item["id"], 0) + 1 / (k + rank + 1)
        chunks[item["id"]] = item
    for rank, item in enumerate(sparse):
        scores[item["id"]] = scores.get(item["id"], 0) + 1 / (k + rank + 1)
        chunks.setdefault(item["id"], item)
    return [chunks[i] for i in sorted(scores, key=scores.get, reverse=True)]


def hybrid_retrieve(query: str, query_embedding: list[float], top_k: int = 20,
                     document_id: str | None = None) -> list[dict]:
    dense = [r.model_dump() for r in vector_store.query(query_embedding, top_k, document_id)]
    sparse = bm25_index.search(query, top_k, document_id)
    return reciprocal_rank_fusion(dense, sparse)
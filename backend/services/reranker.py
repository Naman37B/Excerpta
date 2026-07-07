from flashrank import Ranker, RerankRequest

# Lazy singleton, same reasoning as embeddings.py's _get_embedding_model():
# instantiating Ranker() downloads/loads its model files immediately, so
# doing it at module level meant merely importing this file (which
# api/main.py does) paid that cost — even for tests that never rerank
# anything.
_ranker = None


def _get_ranker():
    global _ranker
    if _ranker is None:
        _ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", max_length=512)
    return _ranker


def rerank(query: str, passages: list[dict], min_score: float = 0.7) -> list[dict]:
    # ranker.rerank() returns bare {id, text, score} objects — it never saw
    # metadata, because the request below only sends id/text. Look the
    # original passage back up by id so metadata survives into the output.
    passage_map = {p["id"]: p for p in passages}
    request = RerankRequest(query=query, passages=[{"id": p["id"], "text": p["text"]} for p in passages])

    reranked = []
    for r in _get_ranker().rerank(request):
        if r["score"] >= min_score:
            original = passage_map[r["id"]]
            original["rerank_score"] = r["score"]
            reranked.append(original)
    return reranked
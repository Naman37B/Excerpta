# Excerpta

Local, fully-offline PDF question answering. Upload a document, ask it questions, get answers that cite the exact page they came from — no cloud APIs anywhere in the pipeline.

Built and tuned for an 8GB laptop GPU (RTX 5070 Laptop GPU + Intel Core Ultra 9 285H), but the VRAM isolation below is what actually makes it portable to smaller hardware, not the specific model choices.

## Architecture

- **Ingestion** — PyMuPDF (`pymupdf4llm`) extracts structured Markdown so tables don't get flattened into unreadable text. Sentences are packed into ~370-token chunks (sized to leave headroom inside FlashRank's 512-token rerank ceiling), then each chunk gets a short LLM-generated prefix situating it in the document (Anthropic's Contextual Retrieval technique) before embedding.
- **Retrieval** — Dense search (ChromaDB, BGE-M3 embeddings) and sparse search (BM25) run independently and get merged with Reciprocal Rank Fusion, then reranked with FlashRank against a hard confidence floor — if nothing clears it, the system says so instead of guessing.
- **Generation** — Llama 3.1 8B via Ollama, streamed to the frontend over Server-Sent Events, with the grounding citations sent as their own event before the first token.
- **Evaluation** — a parametrized DeepEval suite (`backend/tests/test_evals.py`) runs the real pipeline against a golden set of queries with known-correct pages, judged by a local model — not mocked data, and no calls leave the machine.

**Memory defenses.** BGE-M3 and FlashRank are isolated to the CPU; the GPU is reserved entirely for Ollama. `num_ctx` is pinned to 6144 rather than left to float, specifically to avoid the 5–10x slowdown that comes from silently spilling into system RAM. `OLLAMA_MAX_LOADED_MODELS=2` and `OLLAMA_NUM_PARALLEL=1` keep both the chat model and the small contextual-retrieval model resident without fighting each other for VRAM.

**Vector store interface.** `BaseVectorStore` in `backend/services/embeddings.py` is the only thing the rest of the app talks to — swapping ChromaDB for Qdrant at real scale means writing one new class against that interface, not touching any caller.

## Setup

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

ollama pull llama3.1:8b
ollama pull qwen2.5:0.5b
```

Lock the memory budget so the two models don't evict each other:

```bash
sudo systemctl edit ollama.service
```
```ini
[Service]
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_NUM_PARALLEL=1"
```
```bash
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

Run the backend from inside `backend/` (the import paths assume this as the working directory):

```bash
uvicorn api.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Testing

```bash
cd backend
pytest -m "not llm_eval"          # fast, no LLM — what CI runs
pytest -m llm_eval -v             # the real golden-set evaluation, run locally
```

<img width="2880" height="1800" alt="01-empty-archive" src="https://github.com/user-attachments/assets/3543404e-0f91-465f-8078-c4a27146edce" />

<img width="2880" height="1800" alt="02-archive-ready" src="https://github.com/user-attachments/assets/6bece7e1-1445-4290-9705-c3c600ba82e8" />

<img width="2880" height="1800" alt="03-upload-processing" src="https://github.com/user-attachments/assets/ed314705-0f8d-4520-9f45-beca0c258e1d" />

<img width="2880" height="1800" alt="04-upload-indexed" src="https://github.com/user-attachments/assets/7354241c-b7de-4dff-946e-a342f57baf47" />

<img width="2880" height="1800" alt="05-answer-streaming" src="https://github.com/user-attachments/assets/cc5f8dfe-841b-4495-ae73-283ef5f02ee0" />

<img width="2880" height="1800" alt="06-answer-with-citations" src="https://github.com/user-attachments/assets/b2580cc0-1386-4cf1-94c7-e8d531254934" />

<img width="2880" height="1800" alt="07-not-found" src="https://github.com/user-attachments/assets/f0d35171-e435-42f6-a030-a867963742f8" />

<img width="2880" height="1800" alt="08-scoped-to-one-document" src="https://github.com/user-attachments/assets/f5943054-2e8c-4a5e-99af-5bf7fc6e5cc5" />

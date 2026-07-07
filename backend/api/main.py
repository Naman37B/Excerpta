import json
import uuid
from fastapi import FastAPI, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import ollama

from database.tracker import create_job, update_job_status, get_job, list_completed_documents
from services.retriever import hybrid_retrieve, bm25_index
from services.reranker import rerank
from services.embeddings import embed_chunks

app = FastAPI()
MAX_UPLOAD_BYTES = 15 * 1024 * 1024

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # the Next.js dev server, not "*"
    allow_credentials=False,  # nothing here uses cookies/auth — "*" + credentials=True
                               # lets any site your browser visits read responses from
                               # this backend (this exact combo is CVE-2026-32610)
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def limit_upload_size(request, call_next):
    if request.url.path == "/upload" and request.method == "POST":
        if int(request.headers.get("content-length", 0)) > MAX_UPLOAD_BYTES:
            return JSONResponse(status_code=413, content={"detail": "File exceeds 15MB limit."})
    return await call_next(request)

def run_ingestion_pipeline(job_id: str, document_id: str, contents: bytes, filename: str):
    """Executes Phase 2 and 3 in sequence as defined in the blueprint."""
    try:
        from services.pdf import process_document
        from services.embeddings import vector_store
        
        update_job_status(job_id, "Extracting, contextualizing, and chunking...")
        chunks = process_document(document_id, contents)
        
        if not chunks:
            update_job_status(job_id, "Failed: No readable text found.")
            return

        update_job_status(job_id, "Embedding vectors on CPU...")
        texts = [c["text"] for c in chunks]
        ids = [c["id"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        
        embeddings = embed_chunks(texts)
        
        update_job_status(job_id, "Updating Dense and Sparse indexes...")
        vector_store.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        bm25_index.add_document(new_ids=ids, new_texts=texts, new_metadatas=metadatas)
        
        update_job_status(job_id, "Complete")
    except Exception as e:
        update_job_status(job_id, f"Failed: {str(e)}")

@app.post("/upload")
async def upload_document(file: UploadFile, background_tasks: BackgroundTasks):
    header = await file.read(5)
    if header != b"%PDF-":
        raise HTTPException(status_code=400, detail="File is not a valid PDF.")
    await file.seek(0)
    contents = await file.read()

    job_id, document_id = str(uuid.uuid4()), str(uuid.uuid4())
    create_job(job_id, document_id, filename=file.filename, status="Processing")
    background_tasks.add_task(run_ingestion_pipeline, job_id, document_id, contents, file.filename)
    return {"job_id": job_id, "document_id": document_id}

@app.get("/status/{job_id}")
async def status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job

@app.get("/documents")
async def documents():
    return list_completed_documents()

@app.get("/chat")   
async def chat(query: str, document_id: str | None = None):
    query_embedding = embed_chunks([query])[0]
    candidates = hybrid_retrieve(query, query_embedding, top_k=20, document_id=document_id)
    reranked = rerank(query, candidates, min_score=0.0)

    def sse(event: str, data: dict | list) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    if not reranked:
        async def not_found():
            yield sse("token", {"token": "I could not find information regarding this in the uploaded document."})
            yield sse("done", {})
        return StreamingResponse(not_found(), media_type="text/event-stream")

    context = "\n\n".join(r["text"] for r in reranked[:5])
    prompt = f"Answer using only this context:\n{context}\n\nQuestion: {query}"

    def token_stream():
        citations = [
            {
                "id": r["id"],
                "page": r["metadata"].get("page"),
                "document_id": r["metadata"].get("document_id"),
                "snippet": r["text"][:220] + ("…" if len(r["text"]) > 220 else ""),
            }
            for r in reranked[:5]
        ]
        yield sse("citations", citations)

        for part in ollama.chat(model="llama3.1:8b",
                                 messages=[{"role": "user", "content": prompt}],
                                 stream=True, options={"num_ctx": 6144}):
            yield sse("token", {"token": part["message"]["content"]})

        # EventSource's onerror fires for both a clean stream end and a real
        # connection failure — an explicit event lets the frontend tell them
        # apart instead of guessing.
        yield sse("done", {})

    return StreamingResponse(token_stream(), media_type="text/event-stream")
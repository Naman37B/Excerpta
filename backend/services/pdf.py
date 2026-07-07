import nltk
import pymupdf
import pymupdf4llm
import ollama
from transformers import AutoTokenizer
from nltk.tokenize import sent_tokenize

# 1. Self-healing NLTK setup for modern environments[cite: 4]
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)

# 2. Initialize the tokenizer to match our BGE-M3 embedding model[cite: 4]
tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3")
# FlashRank's cross-encoder ceiling is 512 tokens for query+passage combined.
# The ~20-word context prefix generated below adds ~25-30 tokens on top of
# each raw chunk before rerank time, so capping raw chunks at 400 actually
# left only ~85-90 tokens for the query, not the ~110 originally estimated.
# 370 keeps real headroom (~370 chunk + ~30 prefix + ~110 query ≈ 510).
MAX_TOKENS_PER_CHUNK = 370

def extract_pages(pdf_bytes: bytes) -> list[tuple[int, str]]:
    """
    Opens the PDF directly from memory and extracts structured Markdown.
    Returns: [(page_number (1-indexed), markdown_text), ...]
    """
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        chunks = pymupdf4llm.to_markdown(doc, page_chunks=True)
        
        safe_pages = []
        for i, chunk in enumerate(chunks):
            # Safely fetch metadata, defaulting to the loop index 'i' if 'page' is missing
            meta = chunk.get("metadata") or {}
            page_num = meta.get("page", i) + 1
            safe_pages.append((page_num, chunk.get("text", "")))
            
        return safe_pages

def _split_oversized(sentence: str, max_tokens: int) -> list[str]:
    """A markdown table often has no sentence-ending punctuation, so
    sent_tokenize can hand back one giant 'sentence' — split it on lines
    (table rows) so nothing downstream silently exceeds the token budget."""
    lines = sentence.split("\n")
    pieces, current, current_len = [], [], 0
    for line in lines:
        line_tokens = len(tokenizer.encode(line, add_special_tokens=False))
        if current_len + line_tokens > max_tokens and current:
            pieces.append("\n".join(current))
            current, current_len = [line], line_tokens
        else:
            current.append(line)
            current_len += line_tokens
    if current:
        pieces.append("\n".join(current))
    return pieces or [sentence]

def chunk_text_by_sentences(text: str) -> list[str]:
    """
    Splits text into sentences and packs them up to MAX_TOKENS_PER_CHUNK.
    """
    sentences = sent_tokenize(text)
    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        # Measure token length exactly as the embedding model will see it
        sentence_tokens = len(tokenizer.encode(sentence, add_special_tokens=False))

        if sentence_tokens > MAX_TOKENS_PER_CHUNK:
            # A single "sentence" (often a whole markdown table) already
            # exceeds the budget on its own — flush what's pending, then
            # split this one further rather than let it through oversized.
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk, current_length = [], 0
            chunks.extend(_split_oversized(sentence, MAX_TOKENS_PER_CHUNK))
            continue

        if current_length + sentence_tokens > MAX_TOKENS_PER_CHUNK and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
            current_length = sentence_tokens
        else:
            current_chunk.append(sentence)
            current_length += sentence_tokens
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def generate_chunk_context(document_excerpt: str, chunk_text: str) -> str:
    """
    Uses the lightweight Qwen model to generate a situating prefix for the chunk[cite: 4].
    """
    prompt = f"""<document>
{document_excerpt}
</document>
<chunk>
{chunk_text}
</chunk>
Write one short sentence (max 20 words) situating this chunk within the document above, to prepend to it for search. Answer with only that sentence."""
    
    response = ollama.chat(
        model="qwen2.5:0.5b", 
        messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"].strip()

def process_document(document_id: str, pdf_bytes: bytes) -> list[dict]:
    """
    Master pipeline for the PDF file. Extracts, chunks, contextualizes, and assigns IDs[cite: 4].
    """
    pages = extract_pages(pdf_bytes)
    if not pages:
        return []
    
    # Create a simple document excerpt (e.g., first 3000 characters) 
    # to feed Qwen so it understands the global context without reloading the whole PDF[cite: 4].
    full_text = "\n".join([text for _, text in pages])
    document_excerpt = full_text[:3000] 
    
    processed_chunks = []
    
    for page_num, page_text in pages:
        raw_chunks = chunk_text_by_sentences(page_text)
        
        for i, raw_chunk in enumerate(raw_chunks):
            # Generate the contextual prefix
            prefix = generate_chunk_context(document_excerpt, raw_chunk)
            contextualized_text = f"{prefix}\n\n{raw_chunk}"
            
            # Generate the shared stable ID for RRF mapping[cite: 4]
            chunk_id = f"{document_id}_p{page_num}_c{i}"
            
            processed_chunks.append({
                "id": chunk_id,
                "text": contextualized_text,
                "metadata": {
                    "document_id": document_id,
                    "page": page_num
                }
            })
            
    return processed_chunks
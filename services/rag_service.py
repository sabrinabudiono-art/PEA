"""Lightweight RAG service: chunk, embed, store, and retrieve document text."""
import os
import numpy as np
from openai import OpenAI
from models import db, DocumentChunk

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_MAX_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, max_tokens: int = CHUNK_MAX_TOKENS,
               overlap: int = CHUNK_OVERLAP_TOKENS) -> list[str]:
    """Split *text* into overlapping chunks of roughly *max_tokens* words.

    Uses a simple word-level split (1 token ≈ 1 word) which is good enough
    for a lightweight RAG setup without pulling in a tokeniser dependency.
    """
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + max_tokens
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += max_tokens - overlap

    return chunks


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def get_embedding(text: str) -> np.ndarray:
    """Return a 1-D numpy float32 vector for *text* via OpenAI embeddings."""
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return np.array(response.data[0].embedding, dtype=np.float32)


def _embedding_to_bytes(vec: np.ndarray) -> bytes:
    """Serialise a numpy vector to raw bytes for SQLite storage."""
    return vec.tobytes()


def _bytes_to_embedding(raw: bytes) -> np.ndarray:
    """Deserialise raw bytes back to a numpy float32 vector."""
    return np.frombuffer(raw, dtype=np.float32)


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

def store_document_chunks(user_id: int, source_type: str,
                          source_id: int, markdown_text: str) -> int:
    """Chunk *markdown_text*, embed each chunk, and persist to the database.

    Returns the number of chunks stored.
    """
    chunks = chunk_text(markdown_text)
    if not chunks:
        return 0

    for idx, chunk_content in enumerate(chunks):
        vec = get_embedding(chunk_content)
        doc_chunk = DocumentChunk(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            chunk_index=idx,
            content=chunk_content,
            embedding=_embedding_to_bytes(vec),
        )
        db.session.add(doc_chunk)

    db.session.commit()
    return len(chunks)


# ---------------------------------------------------------------------------
# Retrieve
# ---------------------------------------------------------------------------

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def retrieve_relevant_chunks(user_id: int, query: str,
                             top_k: int = 5) -> list[str]:
    """Return the *top_k* most relevant stored chunks for *query*.

    Embeds the query, computes cosine similarity against every chunk
    belonging to the user, and returns the chunk texts ranked by relevance.
    """
    all_chunks = DocumentChunk.query.filter_by(user_id=user_id).all()
    if not all_chunks:
        return []

    query_vec = get_embedding(query)

    scored: list[tuple[float, str]] = []
    for chunk in all_chunks:
        chunk_vec = _bytes_to_embedding(chunk.embedding)
        sim = _cosine_similarity(query_vec, chunk_vec)
        scored.append((sim, chunk.content))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in scored[:top_k]]

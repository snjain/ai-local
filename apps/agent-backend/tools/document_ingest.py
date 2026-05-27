"""Document ingestion pipeline for RAG.

Supports PDF, TXT, and MD files. Extracts text, chunks it,
generates embeddings, and stores in Supabase pgvector.
"""
import io
import os
import hashlib
from typing import List

from openai import AsyncOpenAI
from supabase import Client


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def _split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def _extract_text(file_bytes: bytes, content_type: str) -> str:
    """Extract text from uploaded file."""
    if content_type == "application/pdf" or content_type == "pdf":
        return _extract_text_from_pdf(file_bytes)
    # Treat everything else as plain text
    return file_bytes.decode("utf-8", errors="replace")


async def ingest_document(
    supabase: Client,
    embedding_client: AsyncOpenAI,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    user_id: str,
) -> dict:
    """Ingest a document into the RAG vector store.

    Returns:
        {"status": "ok", "chunks": N, "document_id": "..."}
    """
    # Extract text
    text = _extract_text(file_bytes, content_type)
    if not text.strip():
        return {"status": "error", "message": "No text extracted from file"}

    # Generate document ID
    doc_id = hashlib.sha256(f"{user_id}:{filename}:{len(file_bytes)}".encode()).hexdigest()[:16]

    # Chunk text
    chunks = _split_text(text)
    if not chunks:
        return {"status": "error", "message": "Text too short to chunk"}

    # Generate embeddings for each chunk
    embeddings = []
    for i, chunk in enumerate(chunks):
        resp = await embedding_client.embeddings.create(
            model=os.getenv("EMBEDDING_MODEL_CHOICE", "nomic-embed-text"),
            input=chunk,
        )
        embedding = resp.data[0].embedding
        embeddings.append({
            "document_id": doc_id,
            "chunk_index": i,
            "content": chunk,
            "embedding": embedding,
            "metadata": {"source": filename, "user_id": user_id, "chunk": i},
        })

    # Store document metadata
    supabase.table("document_metadata").upsert({
        "id": doc_id,
        "title": filename,
        "source": filename,
        "mime_type": content_type,
    }).execute()

    # Store chunks in documents table
    for emb in embeddings:
        supabase.table("documents").insert({
            "content": emb["content"],
            "embedding": emb["embedding"],
            "metadata": emb["metadata"],
        }).execute()

    return {
        "status": "ok",
        "document_id": doc_id,
        "chunks": len(chunks),
        "filename": filename,
    }

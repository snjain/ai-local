"""Database operations for the RAG pipeline."""
from typing import List, Dict, Any, Optional
import os
import json
import base64
from supabase import create_client, Client

from text_processor import (
    chunk_text,
    create_embeddings,
    is_tabular_file,
    extract_schema_from_csv,
    extract_rows_from_csv,
)

_supabase = None


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        _supabase = create_client(supabase_url, supabase_key)
    return _supabase


def delete_document_by_file_id(file_id: str) -> None:
    """Delete all records for a specific file ID."""
    try:
        get_supabase().table("documents").delete().eq("metadata->>file_id", file_id).execute()
        try:
            get_supabase().table("document_rows").delete().eq("dataset_id", file_id).execute()
        except Exception:
            pass
        try:
            get_supabase().table("document_metadata").delete().eq("id", file_id).execute()
        except Exception:
            pass
    except Exception as e:
        print(f"Error deleting documents: {e}")


def insert_document_chunks(
    chunks: List[str],
    embeddings: List[List[float]],
    file_id: str,
    file_url: str,
    file_title: str,
    mime_type: str,
    file_contents: bytes | None = None,
) -> None:
    """Insert document chunks with embeddings into Supabase."""
    try:
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            file_bytes_str = base64.b64encode(file_contents).decode("utf-8") if file_contents else None
            meta = {
                "file_id": file_id,
                "file_url": file_url,
                "file_title": file_title,
                "mime_type": mime_type,
                "chunk_index": i,
            }
            if file_bytes_str:
                meta["file_contents"] = file_bytes_str

            get_supabase().table("documents").insert(
                {"content": chunk, "metadata": meta, "embedding": embedding}
            ).execute()
    except Exception as e:
        print(f"Error inserting chunks: {e}")


def insert_or_update_document_metadata(
    file_id: str, file_title: str, file_url: str, schema: Optional[List[str]] = None
) -> None:
    """Insert or update document metadata."""
    try:
        response = get_supabase().table("document_metadata").select("*").eq("id", file_id).execute()
        data = {"id": file_id, "title": file_title, "url": file_url}
        if schema:
            data["schema"] = json.dumps(schema)

        if response.data and len(response.data) > 0:
            get_supabase().table("document_metadata").update(data).eq("id", file_id).execute()
        else:
            get_supabase().table("document_metadata").insert(data).execute()
    except Exception as e:
        print(f"Error updating metadata: {e}")


def insert_document_rows(file_id: str, rows: List[Dict[str, Any]]) -> None:
    """Insert rows from a tabular file into document_rows."""
    try:
        get_supabase().table("document_rows").delete().eq("dataset_id", file_id).execute()
        for row in rows:
            get_supabase().table("document_rows").insert(
                {"dataset_id": file_id, "row_data": row}
            ).execute()
    except Exception as e:
        print(f"Error inserting rows: {e}")


def process_file_for_rag(
    file_content: bytes,
    text: str,
    file_id: str,
    file_url: str,
    file_title: str,
    mime_type: str = None,
    config: Dict[str, Any] = None,
) -> bool:
    """Process a file for the RAG pipeline."""
    try:
        delete_document_by_file_id(file_id)

        is_tabular = False
        schema = None
        if mime_type:
            is_tabular = is_tabular_file(mime_type, config)
        if is_tabular:
            schema = extract_schema_from_csv(file_content)

        insert_or_update_document_metadata(file_id, file_title, file_url, schema)

        if is_tabular:
            rows = extract_rows_from_csv(file_content)
            if rows:
                insert_document_rows(file_id, rows)

        tp = config.get("text_processing", {}) if config else {}
        chunk_size = tp.get("default_chunk_size", 400)
        chunk_overlap = tp.get("default_chunk_overlap", 0)

        chunks = chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
        if not chunks:
            return True

        embeddings = create_embeddings(chunks)

        if mime_type and mime_type.startswith("image"):
            insert_document_chunks(chunks, embeddings, file_id, file_url, file_title, mime_type, file_content)
        else:
            insert_document_chunks(chunks, embeddings, file_id, file_url, file_title, mime_type)

        return True
    except Exception as e:
        print(f"Error processing file: {e}")
        return False

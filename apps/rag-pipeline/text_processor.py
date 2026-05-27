"""Text extraction, chunking, and embedding for the RAG pipeline."""
import io
import csv
import tempfile
import os
from typing import List, Dict, Any
from openai import OpenAI
from pathlib import Path

try:
    import pypdf
except ImportError:
    pypdf = None

_openai_client = None


def get_openai_client():
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("EMBEDDING_API_KEY", "") or os.getenv("LLM_API_KEY", "")
        base_url = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
        _openai_client = OpenAI(api_key=api_key or "dummy-key-for-import", base_url=base_url)
    return _openai_client


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 0) -> List[str]:
    """Split text into chunks of specified size with optional overlap."""
    if not text:
        return []
    text = text.replace("\r", "")
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i : i + chunk_size]
        if chunk:
            chunks.append(chunk)
    return chunks


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from a PDF file."""
    if pypdf is None:
        return "[PDF extraction requires pypdf package]"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file_content)
        temp_file_path = temp_file.name

    try:
        with open(temp_file_path, "rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        return text
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def extract_text_from_file(
    file_content: bytes, mime_type: str, file_name: str, config: Dict[str, Any] = None
) -> str:
    """Extract text from a file based on its MIME type."""
    supported = config.get("supported_mime_types", []) if config else []

    if "application/pdf" in mime_type:
        return extract_text_from_pdf(file_content)
    elif mime_type.startswith("image"):
        return file_name
    elif config and any(mime_type.startswith(t) for t in supported):
        return file_content.decode("utf-8", errors="replace")
    else:
        return file_content.decode("utf-8", errors="replace")


def create_embeddings(texts: List[str]) -> List[List[float]]:
    """Create embeddings for a list of text chunks using OpenAI."""
    if not texts:
        return []
    model = os.getenv("EMBEDDING_MODEL_CHOICE", "text-embedding-3-small")
    response = get_openai_client().embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def is_tabular_file(mime_type: str, config: Dict[str, Any] = None) -> bool:
    """Check if a file is tabular based on its MIME type."""
    tabular = [
        "csv",
        "xlsx",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.google-apps.spreadsheet",
    ]
    if config and "tabular_mime_types" in config:
        tabular = config["tabular_mime_types"]
    return any(mime_type.startswith(t) for t in tabular)


def extract_schema_from_csv(file_content: bytes) -> List[str]:
    """Extract column names from a CSV file."""
    try:
        text = file_content.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        return next(reader)
    except Exception as e:
        print(f"Error extracting schema: {e}")
        return []


def extract_rows_from_csv(file_content: bytes) -> List[Dict[str, Any]]:
    """Extract rows from a CSV file as a list of dictionaries."""
    try:
        text = file_content.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
    except Exception as e:
        print(f"Error extracting rows: {e}")
        return []

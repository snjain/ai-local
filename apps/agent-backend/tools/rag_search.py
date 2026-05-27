"""RAG document retrieval tools."""

from openai import AsyncOpenAI
from supabase import Client


async def retrieve_relevant_documents(
    supabase: Client,
    embedding_client: AsyncOpenAI,
    user_query: str,
    top_k: int = 4,
) -> str:
    """
    Retrieve relevant document chunks from Supabase pgvector.
    """
    try:
        # Generate embedding for the query
        response = await embedding_client.embeddings.create(
            model="nomic-embed-text",  # Will be overridden by config
            input=user_query,
        )
        query_embedding = response.data[0].embedding

        # Search pgvector
        result = supabase.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.5,
                "match_count": top_k,
            },
        ).execute()

        documents = result.data
        if not documents:
            return "No relevant documents found."

        formatted = []
        for i, doc in enumerate(documents, 1):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            source = metadata.get("source", "Unknown")
            formatted.append(f"[Doc {i}] Source: {source}\n{content}\n")

        return "\n---\n".join(formatted)
    except Exception as e:
        return f"RAG retrieval error: {e}"


async def list_documents(supabase: Client) -> str:
    """List all documents in the database."""
    try:
        result = supabase.table("document_metadata").select("*").execute()
        docs = result.data
        if not docs:
            return "No documents indexed yet."

        lines = [f"Indexed Documents ({len(docs)}):"]
        for doc in docs:
            title = doc.get("title", "Untitled")
            doc_id = doc.get("id", "?")
            lines.append(f"  - {title} (ID: {doc_id})")

        return "\n".join(lines)
    except Exception as e:
        return f"List documents error: {e}"

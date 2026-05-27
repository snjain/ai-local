"""Database utilities for conversation history and rate limiting."""
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import random
import string
import json

from supabase import Client
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter


def generate_session_id(user_id: str) -> str:
    """Generate a unique session ID."""
    random_str = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
    return f"{user_id}~{random_str}"


async def fetch_conversation_history(supabase: Client, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch recent conversation history."""
    try:
        response = (
            supabase.table("messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data[::-1] if response.data else []
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []


async def create_conversation(supabase: Client, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    """Create a new conversation record."""
    try:
        response = (
            supabase.table("conversations")
            .insert({"user_id": user_id, "session_id": session_id})
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error creating conversation: {e}")
        return None


async def update_conversation_title(supabase: Client, session_id: str, title: str) -> None:
    """Update conversation title."""
    try:
        supabase.table("conversations").update({"title": title}).eq("session_id", session_id).execute()
    except Exception as e:
        print(f"Error updating title: {e}")


async def store_message(
    supabase: Client,
    session_id: str,
    message_type: str,
    content: str,
    message_data: Optional[str] = None,
    data: Optional[Dict] = None,
) -> None:
    """Store a message in the database."""
    message_obj = {"type": message_type, "content": content}
    if data:
        message_obj["data"] = data

    insert_data = {"session_id": session_id, "message": message_obj}
    if message_data:
        insert_data["message_data"] = message_data

    try:
        supabase.table("messages").insert(insert_data).execute()
    except Exception as e:
        print(f"Error storing message: {e}")


async def convert_history_to_pydantic_format(conversation_history: List[Dict[str, Any]]) -> List[ModelMessage]:
    """Convert DB history to Pydantic AI message format."""
    messages: List[ModelMessage] = []
    for msg in conversation_history:
        if msg.get("message_data"):
            try:
                messages.extend(ModelMessagesTypeAdapter.validate_json(msg["message_data"]))
            except Exception as e:
                print(f"Error parsing message_data: {e}")
    return messages


async def check_rate_limit(supabase: Client, user_id: str, rate_limit: int = 10) -> bool:
    """Check if user is within rate limit (requests per minute)."""
    try:
        one_minute_ago = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        response = (
            supabase.table("requests")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .gte("timestamp", one_minute_ago)
            .execute()
        )
        count = response.count if hasattr(response, "count") else 0
        return count < rate_limit
    except Exception as e:
        print(f"Error checking rate limit: {e}")
        return True


async def store_request(supabase: Client, request_id: str, user_id: str, query: str) -> None:
    """Store a request for rate limiting."""
    try:
        supabase.table("requests").insert({
            "id": request_id,
            "user_id": user_id,
            "user_query": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        print(f"Error storing request: {e}")


async def list_conversations(supabase: Client, user_id: str) -> List[Dict[str, Any]]:
    """List all conversations for a user."""
    try:
        response = (
            supabase.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .order("last_message_at", desc=True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"Error listing conversations: {e}")
        return []

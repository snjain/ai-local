from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai import Agent, RunContext
from dataclasses import dataclass
from dotenv import load_dotenv
from openai import AsyncOpenAI
from httpx import AsyncClient
from supabase import Client
from pathlib import Path
import os

from prompt import AGENT_SYSTEM_PROMPT
from tools.web_search import web_search as _web_search
from tools.rag_search import retrieve_relevant_documents as _rag_search
from tools.code_execution import execute_python_code
from tools.image_analysis import analyze_image
from tools.sql_query import execute_sql_query
from memory.mem0_client import get_mem0_client

# Load .env from project root (3 levels up: agent-backend/ -> apps/ -> project/)
project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / '.env', override=True)


def get_model():
    llm = os.getenv('LLM_CHOICE') or 'gpt-4o-mini'
    base_url = os.getenv('LLM_BASE_URL') or 'https://api.openai.com/v1'
    api_key = os.getenv('LLM_API_KEY') or 'ollama'
    return OpenAIChatModel(llm, provider=OpenAIProvider(base_url=base_url, api_key=api_key))


@dataclass
class AgentDeps:
    supabase: Client
    embedding_client: AsyncOpenAI
    http_client: AsyncClient
    brave_api_key: str | None
    searxng_base_url: str | None
    memories: str


agent = Agent(get_model(), system_prompt=AGENT_SYSTEM_PROMPT, deps_type=AgentDeps, retries=2)


@agent.system_prompt
def add_memories(ctx: RunContext[str]) -> str:
    return f"\nUser Memories:\n{ctx.deps.memories}"


@agent.tool
async def web_search(ctx: RunContext[AgentDeps], query: str) -> str:
    """Search the web for current information."""
    return await _web_search(query, ctx.deps.http_client, ctx.deps.brave_api_key, ctx.deps.searxng_base_url)


@agent.tool
async def retrieve_relevant_documents(ctx: RunContext[AgentDeps], user_query: str) -> str:
    """Retrieve relevant documents from the knowledge base (RAG)."""
    return await _rag_search(ctx.deps.supabase, ctx.deps.embedding_client, user_query)


@agent.tool
async def code_execution(ctx: RunContext[AgentDeps], code: str) -> str:
    """Execute Python code in a sandboxed environment and return output."""
    return await execute_python_code(code)


@agent.tool
async def image_analysis(ctx: RunContext[AgentDeps], image_path: str, query: str) -> str:
    """Analyze an image using a vision model. Provide a file path and a question."""
    return await analyze_image(image_path, query)


@agent.tool
async def sql_query(ctx: RunContext[AgentDeps], query: str) -> str:
    """Execute a read-only SQL query against the database via Supabase. Only SELECT/WITH queries allowed."""
    return await execute_sql_query(ctx.deps.supabase, query)

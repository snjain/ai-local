"""FastAPI server for the Pydantic AI Agent."""

import os
import json
import base64
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Security, Depends, Request, UploadFile, File
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from httpx import AsyncClient
from pydantic import BaseModel

from agent import agent, AgentDeps
from clients import get_embedding_client, get_supabase_client
from memory.mem0_client import get_mem0_client
from db_utils import (
    generate_session_id,
    fetch_conversation_history,
    create_conversation,
    update_conversation_title,
    store_message,
    convert_history_to_pydantic_format,
    check_rate_limit,
    store_request,
    list_conversations,
)

# LangGraph architecture modules (Module 7)
from graphs.routing_graph import workflow as routing_workflow, create_initial_state as routing_initial_state
from graphs.parallel_graph import workflow as parallel_workflow, create_initial_state as parallel_initial_state
from graphs.supervisor_graph import workflow as supervisor_workflow, create_initial_state as supervisor_initial_state
from graphs.guardrail_graph import workflow as guardrail_workflow, create_initial_state as guardrail_initial_state


# ─── Request/Response Models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    thread_id: str


class AgentRequest(BaseModel):
    query: str
    user_id: str
    request_id: str
    session_id: str = ""
    files: Optional[List[dict]] = None


class WebSearchRequest(BaseModel):
    query: str


class CodeExecutionRequest(BaseModel):
    code: str


class SqlQueryRequest(BaseModel):
    query: str


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage shared HTTP client lifecycle."""
    app.state.http_client = AsyncClient()
    app.state.supabase = get_supabase_client()
    app.state.embedding_client = get_embedding_client()
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="Pydantic AI Agent API",
    description="REST API for the local AI agent with Supabase auth, conversation history, and tool calling.",
    version="0.2.0",
    lifespan=lifespan,
)
security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Auth ─────────────────────────────────────────────────────────────────────

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """Verify JWT locally using Supabase JWT_SECRET (avoids Kong routing issues in Docker)."""
    import jwt

    try:
        token = credentials.credentials
        jwt_secret = os.getenv("JWT_SECRET", "")
        if not jwt_secret:
            raise HTTPException(status_code=500, detail="JWT_SECRET not configured")

        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"], audience="authenticated")
        return {
            "id": payload.get("sub"),
            "aud": payload.get("aud"),
            "role": payload.get("role"),
            "email": payload.get("email"),
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {e}")


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ─── Simple Chat (no auth) ────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    http_client = app.state.http_client
    supabase = app.state.supabase
    embedding_client = app.state.embedding_client

    try:
        mem = get_mem0_client()
        results = mem.search(query=req.message, user_id="api_user", limit=3)
        memories = "\n".join(f"- {r['memory']}" for r in results.get("results", []))
    except Exception:
        memories = ""

    # ── Automatic RAG retrieval ──
    rag_context = ""
    try:
        from tools.rag_search import retrieve_relevant_documents
        rag_result = await retrieve_relevant_documents(supabase, embedding_client, req.message)
        if rag_result and "No relevant documents" not in rag_result:
            rag_context = f"\n\n[RELEVANT DOCUMENTS FROM KNOWLEDGE BASE]\n{rag_result}\n\n"
    except Exception as e:
        print(f"RAG retrieval error: {e}")

    enriched_message = req.message
    if rag_context:
        enriched_message = (
            f"Use the following documents from the knowledge base to answer. "
            f"If the documents don't contain the answer, say so.\n\n"
            f"{rag_context}\n"
            f"User question: {req.message}"
        )

    deps = AgentDeps(
        supabase=supabase,
        embedding_client=embedding_client,
        http_client=http_client,
        brave_api_key=os.getenv("BRAVE_API_KEY") or None,
        searxng_base_url=os.getenv("SEARXNG_BASE_URL") or None,
        memories=memories,
    )
    result = await agent.run(enriched_message, deps=deps)
    return ChatResponse(response=result.output, thread_id=req.thread_id)


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    if not req.stream:
        raise HTTPException(status_code=400, detail="Set stream=true for SSE")

    http_client = app.state.http_client
    supabase = app.state.supabase
    embedding_client = app.state.embedding_client

    try:
        mem = get_mem0_client()
        results = mem.search(query=req.message, user_id="api_user", limit=3)
        memories = "\n".join(f"- {r['memory']}" for r in results.get("results", []))
    except Exception:
        memories = ""

    # ── Automatic RAG retrieval ──
    rag_context = ""
    try:
        from tools.rag_search import retrieve_relevant_documents
        rag_result = await retrieve_relevant_documents(supabase, embedding_client, req.message)
        if rag_result and "No relevant documents" not in rag_result:
            rag_context = f"\n\n[RELEVANT DOCUMENTS FROM KNOWLEDGE BASE]\n{rag_result}\n\n"
    except Exception as e:
        print(f"RAG retrieval error: {e}")

    enriched_message = req.message
    if rag_context:
        enriched_message = (
            f"Use the following documents from the knowledge base to answer. "
            f"If the documents don't contain the answer, say so.\n\n"
            f"{rag_context}\n"
            f"User question: {req.message}"
        )

    deps = AgentDeps(
        supabase=supabase,
        embedding_client=embedding_client,
        http_client=http_client,
        brave_api_key=os.getenv("BRAVE_API_KEY") or None,
        searxng_base_url=os.getenv("SEARXNG_BASE_URL") or None,
        memories=memories,
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        async with agent.run_stream(enriched_message, deps=deps) as result:
            async for chunk in result.stream_text(delta=True):
                yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ─── Full Agent Endpoint (auth + history + streaming) ─────────────────────────

async def stream_error_response(error_message: str, session_id: str):
    """Yield a streaming error response."""
    yield json.dumps({"text": error_message}).encode("utf-8") + b"\n"
    yield json.dumps({"text": error_message, "session_id": session_id, "error": error_message, "complete": True}).encode("utf-8") + b"\n"


@app.post("/api/pydantic-agent")
async def pydantic_agent(request: AgentRequest, user: Dict[str, Any] = Depends(verify_token)):
    """Main agent endpoint with auth, conversation history, and streaming."""
    if request.user_id != user.get("id"):
        return StreamingResponse(
            stream_error_response("User ID mismatch", request.session_id),
            media_type="text/plain",
        )

    supabase = app.state.supabase
    http_client = app.state.http_client
    embedding_client = app.state.embedding_client

    # Rate limit check
    rate_ok = await check_rate_limit(supabase, request.user_id)
    if not rate_ok:
        return StreamingResponse(
            stream_error_response("Rate limit exceeded. Please try again later.", request.session_id),
            media_type="text/plain",
        )

    # Track request
    asyncio.create_task(store_request(supabase, request.request_id, request.user_id, request.query))

    session_id = request.session_id
    conversation_record = None

    if not session_id:
        session_id = generate_session_id(request.user_id)
        conversation_record = await create_conversation(supabase, request.user_id, session_id)

    # Store user message
    await store_message(supabase, session_id, "human", request.query)

    # Fetch history
    history = await fetch_conversation_history(supabase, session_id)
    pydantic_messages = await convert_history_to_pydantic_format(history)

    # Memories
    memories_str = ""
    try:
        mem = get_mem0_client()
        mem_results = mem.search(query=request.query, user_id=request.user_id, limit=3)
        memories_str = "\n".join(f"- {r['memory']}" for r in mem_results.get("results", []))
        # Fire-and-forget memory add
        asyncio.create_task(mem.add([{"role": "user", "content": request.query}], user_id=request.user_id))
    except Exception:
        pass

    async def stream_response():
        # ── Automatic RAG retrieval ──
        # Always fetch relevant documents and prepend them to the query
        rag_context = ""
        try:
            from tools.rag_search import retrieve_relevant_documents
            rag_result = await retrieve_relevant_documents(supabase, embedding_client, request.query)
            if rag_result and "No relevant documents" not in rag_result:
                rag_context = f"\n\n[RELEVANT DOCUMENTS FROM KNOWLEDGE BASE]\n{rag_result}\n\n"
        except Exception as e:
            print(f"RAG retrieval error: {e}")

        # Build the enriched prompt
        enriched_query = request.query
        if rag_context:
            enriched_query = (
                f"Use the following documents from the knowledge base to answer. "
                f"If the documents don't contain the answer, say so.\n\n"
                f"{rag_context}\n"
                f"User question: {request.query}"
            )

        deps = AgentDeps(
            supabase=supabase,
            embedding_client=embedding_client,
            http_client=http_client,
            brave_api_key=os.getenv("BRAVE_API_KEY") or None,
            searxng_base_url=os.getenv("SEARXNG_BASE_URL") or None,
            memories=memories_str,
        )

        full_response = ""
        result = await agent.run(enriched_query, deps=deps, message_history=pydantic_messages)
        full_response = result.output

        # Stream the response word-by-word for UI effect
        words = full_response.split(" ")
        for i, word in enumerate(words):
            chunk = " ".join(words[: i + 1])
            yield json.dumps({"text": chunk}).encode("utf-8") + b"\n"
            await asyncio.sleep(0.01)

        # Store AI response
        try:
            message_data = result.new_messages_json()
            await store_message(
                supabase, session_id, "ai", full_response,
                message_data=message_data.decode("utf-8") if isinstance(message_data, bytes) else message_data,
                data={"request_id": request.request_id},
            )
        except Exception as e:
            print(f"Error storing response: {e}")

        # Final chunk
        final = {"text": full_response, "session_id": session_id, "complete": True}
        if conversation_record:
            # Generate title from first message
            title = request.query[:50] + "..." if len(request.query) > 50 else request.query
            await update_conversation_title(supabase, session_id, title)
            final["conversation_title"] = title

        yield json.dumps(final).encode("utf-8") + b"\n"

    return StreamingResponse(stream_response(), media_type="text/plain")


# ─── Architecture Endpoints (Module 7) ────────────────────────────────────────

async def _run_langgraph_stream(
    architecture_name: str,
    workflow,
    create_initial_state,
    request: AgentRequest,
    user: Dict[str, Any],
):
    """Generic LangGraph streaming endpoint."""
    if request.user_id != user.get("id"):
        return StreamingResponse(
            stream_error_response("User ID mismatch", request.session_id),
            media_type="text/plain",
        )

    supabase = app.state.supabase

    rate_ok = await check_rate_limit(supabase, request.user_id)
    if not rate_ok:
        return StreamingResponse(
            stream_error_response("Rate limit exceeded. Please try again later.", request.session_id),
            media_type="text/plain",
        )

    asyncio.create_task(store_request(supabase, request.request_id, request.user_id, request.query))

    session_id = request.session_id
    conversation_record = None

    if not session_id:
        session_id = generate_session_id(request.user_id)
        conversation_record = await create_conversation(supabase, request.user_id, session_id)

    await store_message(supabase, session_id, "human", request.query)

    history = await fetch_conversation_history(supabase, session_id)
    pydantic_messages = await convert_history_to_pydantic_format(history)

    initial_state = create_initial_state(
        query=request.query,
        session_id=session_id,
        request_id=request.request_id,
        pydantic_message_history=pydantic_messages,
    )

    thread_id = f"{architecture_name}-{session_id}"
    config = {"configurable": {"thread_id": thread_id}}

    async def stream_response():
        full_response = ""
        final_state = None

        try:
            async for stream_mode, chunk in workflow.astream(
                initial_state, config, stream_mode=["custom", "values"]
            ):
                if stream_mode == "custom":
                    if isinstance(chunk, str):
                        full_response += chunk
                        yield json.dumps({"text": full_response}).encode("utf-8") + b"\n"
                    elif isinstance(chunk, bytes):
                        try:
                            decoded = chunk.decode("utf-8")
                            full_response += decoded
                            yield json.dumps({"text": full_response}).encode("utf-8") + b"\n"
                        except:
                            yield chunk
                elif stream_mode == "values":
                    final_state = chunk
        except Exception as e:
            error_msg = f"Streaming error: {e}"
            print(error_msg)
            yield json.dumps({"text": error_msg}).encode("utf-8") + b"\n"

        # Store AI response
        try:
            await store_message(
                supabase, session_id, "ai", full_response,
                data={"request_id": request.request_id, "architecture": architecture_name},
            )
        except Exception as e:
            print(f"Error storing response: {e}")

        final = {
            "text": full_response,
            "session_id": session_id,
            "complete": True,
            "architecture": architecture_name,
        }
        if conversation_record:
            title = request.query[:50] + "..." if len(request.query) > 50 else request.query
            await update_conversation_title(supabase, session_id, title)
            final["conversation_title"] = title

        yield json.dumps(final).encode("utf-8") + b"\n"

    return StreamingResponse(stream_response(), media_type="text/plain")


@app.post("/api/agent-routing")
async def agent_routing(request: AgentRequest, user: Dict[str, Any] = Depends(verify_token)):
    """LLM Routing architecture: route query to specialized agent."""
    return await _run_langgraph_stream("routing", routing_workflow, routing_initial_state, request, user)


@app.post("/api/agent-parallel")
async def agent_parallel(request: AgentRequest, user: Dict[str, Any] = Depends(verify_token)):
    """Parallel Agents architecture: run multiple agents simultaneously."""
    return await _run_langgraph_stream("parallel", parallel_workflow, parallel_initial_state, request, user)


@app.post("/api/agent-supervisor")
async def agent_supervisor(request: AgentRequest, user: Dict[str, Any] = Depends(verify_token)):
    """Supervisor Agent architecture: dynamic iterative delegation."""
    return await _run_langgraph_stream("supervisor", supervisor_workflow, supervisor_initial_state, request, user)


@app.post("/api/agent-guardrail")
async def agent_guardrail(request: AgentRequest, user: Dict[str, Any] = Depends(verify_token)):
    """Guardrail Agent architecture: validate and correct responses."""
    return await _run_langgraph_stream("guardrail", guardrail_workflow, guardrail_initial_state, request, user)


# ─── Conversation Management ──────────────────────────────────────────────────

@app.get("/api/conversations")
async def get_conversations(user: Dict[str, Any] = Depends(verify_token)):
    """List user's conversations."""
    supabase = app.state.supabase
    conversations = await list_conversations(supabase, user["id"])
    return {"conversations": conversations}


@app.get("/api/conversations/{session_id}/messages")
async def get_messages(session_id: str, user: Dict[str, Any] = Depends(verify_token)):
    """Get messages for a conversation."""
    supabase = app.state.supabase
    messages = await fetch_conversation_history(supabase, session_id)
    return {"messages": messages}


# ─── Document Ingestion ───────────────────────────────────────────────────────

@app.post("/api/ingest")
async def ingest_document_endpoint(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(verify_token),
):
    """Upload a document (PDF, TXT, MD) for RAG."""
    from tools.document_ingest import ingest_document

    content = await file.read()
    result = await ingest_document(
        app.state.supabase,
        app.state.embedding_client,
        content,
        file.filename or "unnamed",
        file.content_type or "application/octet-stream",
        user["id"],
    )
    if result.get("status") != "ok":
        raise HTTPException(status_code=400, detail=result.get("message", "Ingest failed"))
    return result


# ─── Direct Tool Endpoints ────────────────────────────────────────────────────

@app.post("/tools/web_search")
async def web_search(req: WebSearchRequest) -> dict:
    from tools.web_search import web_search

    http_client = app.state.http_client
    result = await web_search(
        req.query, http_client,
        os.getenv("BRAVE_API_KEY") or None,
        os.getenv("SEARXNG_BASE_URL") or None,
    )
    return {"query": req.query, "results": result}


@app.post("/tools/rag")
async def rag_search(req: WebSearchRequest) -> dict:
    from tools.rag_search import retrieve_relevant_documents

    result = await retrieve_relevant_documents(
        app.state.supabase, app.state.embedding_client, req.query
    )
    return {"query": req.query, "results": result}


@app.post("/tools/code")
async def code_execution(req: CodeExecutionRequest) -> dict:
    from tools.code_execution import execute_python_code

    result = await execute_python_code(req.code)
    return {"output": result}


@app.post("/tools/sql")
async def sql_query(req: SqlQueryRequest) -> dict:
    from tools.sql_query import execute_sql_query

    result = await execute_sql_query(app.state.supabase, req.query)
    return {"output": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

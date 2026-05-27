# Plan: Integrate Pydantic AI Agent into Local AI Stack

## Goal
Port the `4_Pydantic_AI_Agent` from the Dynamous AI Agent Mastery course into this local AI codebase (`/Users/snjain/github/ai`). The agent will run as a native Python service alongside the existing Docker stack, leveraging the already-running infrastructure (Supabase, SearXNG, Ollama) rather than bringing its own.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Local AI Stack                               │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   n8n       │  │ Open WebUI  │  │   Flowise   │  │   Neo4j    │ │
│  │  (5678)     │  │  (8080)     │  │  (3001)     │  │  (7474)    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              pydantic-ai-agent (NEW — native Python)          │   │
│  │                   ┌────────────────────┐                      │   │
│  │  Streamlit UI ───►│  Pydantic AI Agent │◄─── Mem0 (Postgres) │   │
│  │     (8501)        │                    │                      │   │
│  │                   │  Tools: RAG │ Web  │◄─── Supabase/pgvec  │   │
│  │                   │  Search │ Code   │                      │   │
│  │                   └────────────────────┘                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  Supabase   │  │   Qdrant    │  │   SearXNG   │  │  Langfuse  │ │
│  │  (5432)     │  │  (6333)     │  │  (8080)     │  │  (3000)    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
│                                                                      │
│  Ollama runs natively on macOS @ http://host.docker.internal:11434   │
└─────────────────────────────────────────────────────────────────────┘
```

## What Already Exists (Infrastructure)

| Component | Status | How Pydantic Agent Uses It |
|-----------|--------|---------------------------|
| **Supabase (Postgres + pgvector)** | ✅ Running | RAG document store, embeddings table |
| **SearXNG** | ✅ Running | Web search tool (`searxng:8080`) |
| **Ollama** | ✅ Native macOS | LLM + embedding inference |
| **Langfuse** | ✅ Running | Optional: trace agent runs |
| **Qdrant** | ✅ Running | Optional: alternative vector store |
| **Neo4j** | ✅ Running | Optional: graph-based RAG |

## What We Need to Build

### Core Agent Module (`pydantic_ai_agent/`)

```
pydantic_ai_agent/
├── __init__.py
├── agent.py              # Main Pydantic AI agent (ported from source)
├── clients.py            # LLM/db client setup (adapted for local stack)
├── prompt.py             # System prompt
├── tools.py              # Agent tools (web search, RAG, code exec, etc.)
├── streamlit_ui.py       # Chat UI (ported from source)
├── config.py             # NEW: centralized config using pydantic-settings
├── deps.py               # NEW: AgentDeps dataclass + dependency injection
├── memory/
│   ├── __init__.py
│   ├── mem0_client.py    # Long-term memory via Mem0 (Postgres)
│   └── chat_history.py   # Short-term conversation memory
├── rag/
│   ├── __init__.py
│   ├── db_handler.py     # Supabase pgvector operations
│   ├── text_processor.py # Chunking + embeddings
│   ├── local_pipeline.py # File watcher for shared/ directory
│   └── google_pipeline.py# Optional: Google Drive pipeline
├── tools_impl/
│   ├── __init__.py
│   ├── web_search.py     # SearXNG + Brave search
│   ├── image_analysis.py # Vision-capable LLM calls
│   ├── code_execution.py # RestrictedPython sandbox
│   └── sql_query.py      # SQL generation + execution on Supabase
└── tests/
    ├── conftest.py
    ├── test_agent.py
    ├── test_tools.py
    └── test_rag.py
```

### Docker Service (`docker-compose.yml` addition)

```yaml
  pydantic-agent:
    build: ./pydantic_ai_agent
    container_name: pydantic-agent
    restart: unless-stopped
    ports:
      - "8501:8501"    # Streamlit UI
    environment:
      - LLM_PROVIDER=ollama
      - LLM_BASE_URL=http://host.docker.internal:11434/v1
      - LLM_API_KEY=ollama
      - LLM_CHOICE=qwen2.5:14b-instruct-8k
      - EMBEDDING_PROVIDER=ollama
      - EMBEDDING_BASE_URL=http://host.docker.internal:11434/v1
      - EMBEDDING_API_KEY=ollama
      - EMBEDDING_MODEL_CHOICE=nomic-embed-text
      - SUPABASE_URL=http://kong:8000
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/postgres
      - SEARXNG_BASE_URL=http://searxng:8080
      - BRAVE_API_KEY=${BRAVE_API_KEY:-}
      - VISION_LLM_CHOICE=llava:7b
    volumes:
      - ./shared:/data/shared:ro
    depends_on:
      - db
      - searxng
```

> **Alternative**: Run the agent **natively** (outside Docker) using the existing `.venv` for faster iteration, and only containerize for production.

## Implementation Phases

### Phase 0: Project Bootstrap

1. **Create `pydantic_ai_agent/` directory**
2. **Install dependencies** into existing `.venv`:
   ```bash
   uv pip install pydantic-ai mem0ai supabase vecs streamlit openai httpx
   ```
3. **Create `pyproject.toml` entry** (or add to existing)
4. **Add env vars** to root `.env`:
   ```
   # Pydantic AI Agent
   LLM_PROVIDER=ollama
   LLM_BASE_URL=http://host.docker.internal:11434/v1
   LLM_API_KEY=ollama
   LLM_CHOICE=qwen2.5:14b-instruct-8k
   EMBEDDING_PROVIDER=ollama
   EMBEDDING_BASE_URL=http://host.docker.internal:11434/v1
   EMBEDDING_API_KEY=ollama
   EMBEDDING_MODEL_CHOICE=nomic-embed-text
   VISION_LLM_CHOICE=llava:7b
   BRAVE_API_KEY=
   SEARXNG_BASE_URL=http://searxng:8080
   ```
5. **Add `rav` shortcuts**:
   ```yaml
   agent:
     - cd pydantic_ai_agent && streamlit run streamlit_ui.py
   agent-dev:
     - cd pydantic_ai_agent && python -m pytest tests/ -v
   ```

### Phase 1: Core Agent Skeleton

Port the minimal agent from `agent.py`, `prompt.py`, `clients.py`:

- `AgentDeps` dataclass with Supabase + embedding client + HTTP client
- `get_model()` configured for Ollama via OpenAI-compatible API
- Agent instance with system prompt + tool registry (empty initially)
- Health check: agent can respond to a simple prompt via CLI

**Test**: `python -c "from agent import agent; print('Agent loaded')"`

### Phase 2: RAG Pipeline (Local Files)

Adapt the `RAG_Pipeline/Local_Files/` module:

1. **Database schema**: Ensure Supabase has the tables:
   - `documents` (id, content, embedding, metadata)
   - `document_metadata` (id, title, mime_type, source)
   - `document_rows` (for tabular data)
2. **Text processor**: Port `chunk_text()` + `create_embeddings()`
3. **File watcher**: Watch `./shared/` directory (already mounted in n8n)
4. **DB handler**: Port `insert_document_chunks()`, `delete_document_by_file_id()`

**Integration point**: The agent's `retrieve_relevant_documents_tool` queries the same Supabase pgvector table that the n8n RAG workflow uses.

### Phase 3: Agent Tools

Port tools from `tools.py` one by one:

| Tool | Source | Local Adaptation |
|------|--------|-----------------|
| `web_search_tool` | Brave API + SearXNG | Default to SearXNG (already running), Brave as fallback |
| `retrieve_relevant_documents_tool` | RAG query | Supabase pgvector similarity search |
| `list_documents_tool` | List files | Query `document_metadata` table |
| `get_document_content_tool` | Get file content | Fetch from Supabase |
| `execute_sql_query_tool` | SQL on tabular docs | Supabase PostgREST API |
| `execute_safe_code_tool` | RestrictedPython | Same — runs in-process |
| `image_analysis_tool` | Vision LLM | Ollama `llava:7b` via OpenAI-compatible API |
| **Memory tool** (new) | Mem0 | Search + store memories in Postgres |

### Phase 4: Memory System

1. **Mem0 setup**: Configure `mem0ai` with local Postgres (same Supabase DB)
2. **Long-term memory**: Extract + deduplicate memories after each conversation turn
3. **Short-term memory**: Pass `message_history` through Pydantic AI's built-in mechanism
4. **Memory tool**: Agent can `search_memories` and `add_memory`

### Phase 5: Streamlit UI

Port `streamlit_ui.py`:

1. **Chat interface**: Display user/assistant messages
2. **Streaming support**: `agent.iter()` with real-time output
3. **Memory panel**: Show retrieved memories for transparency
4. **Document sidebar**: List indexed documents, upload new ones

### Phase 6: Caddy Route

Add to Caddyfile:
```
{$AGENT_HOSTNAME} {
    reverse_proxy pydantic-agent:8501
}
```

Or if running natively:
```
{$AGENT_HOSTNAME} {
    reverse_proxy host.docker.internal:8501
}
```

### Phase 7: Testing & Polish

1. **Unit tests**: Port existing tests from source
2. **Integration test**: End-to-end chat with RAG + memory + web search
3. **n8n integration**: The Pydantic agent can be called from n8n via HTTP Request node
4. **Documentation**: README with setup instructions

## Key Design Decisions

### 1. Run Native vs. Docker?

**Recommendation: Run native** (outside Docker) during development.

| Approach | Pros | Cons |
|----------|------|------|
| **Native** | Fast iteration, debugger works, direct file access | Needs `.venv` activated |
| **Docker** | Reproducible, consistent env | Slower build, harder to debug |

**Hybrid**: Develop natively, add a `Dockerfile` + compose service for production.

### 2. Shared Data Directory

Both n8n and the Pydantic agent should use `./shared/` as the document drop zone:
- n8n: `Local File Trigger` watches `shared/` → inserts into Supabase
- Pydantic agent: File watcher watches `shared/` → inserts into Supabase (same table)

This means **documents uploaded to `shared/` are available to both n8n workflows and the Pydantic agent**.

### 3. Vector Store: Supabase pgvector vs. Qdrant

**Use Supabase pgvector** (already configured for n8n RAG). The Pydantic agent should query the same `documents` table for consistency.

If Qdrant is preferred later, migrate both n8n and the agent together.

### 4. LLM Choice

Default to Ollama models that support tools:
- **Chat**: `qwen2.5:14b-instruct-8k` (good tool use, fast on Apple Silicon)
- **Vision**: `llava:7b` (image analysis)
- **Embeddings**: `nomic-embed-text` (fast, good quality)

Users can override via `.env` to use OpenAI/OpenRouter.

## File Mapping (Source → Destination)

| Source File | Destination | Notes |
|-------------|-------------|-------|
| `agent.py` | `pydantic_ai_agent/agent.py` | Adapt clients for local stack |
| `clients.py` | `pydantic_ai_agent/clients.py` | Use Supabase URL from `.env` |
| `prompt.py` | `pydantic_ai_agent/prompt.py` | Copy as-is |
| `tools.py` | `pydantic_ai_agent/tools_impl/*.py` | Split into modules |
| `streamlit_ui.py` | `pydantic_ai_agent/streamlit_ui.py` | Adapt imports |
| `RAG_Pipeline/common/db_handler.py` | `pydantic_ai_agent/rag/db_handler.py` | Adapt Supabase client |
| `RAG_Pipeline/common/text_processor.py` | `pydantic_ai_agent/rag/text_processor.py` | Copy as-is |
| `RAG_Pipeline/Local_Files/file_watcher.py` | `pydantic_ai_agent/rag/local_pipeline.py` | Watch `./shared/` |
| `tests/` | `pydantic_ai_agent/tests/` | Port with pytest |

## Environment Variables Required

```bash
# LLM Configuration
LLM_PROVIDER=ollama                    # openai | openrouter | ollama
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_API_KEY=ollama
LLM_CHOICE=qwen2.5:14b-instruct-8k
VISION_LLM_CHOICE=llava:7b

# Embedding Configuration
EMBEDDING_PROVIDER=ollama
EMBEDDING_BASE_URL=http://host.docker.internal:11434/v1
EMBEDDING_API_KEY=ollama
EMBEDDING_MODEL_CHOICE=nomic-embed-text

# Supabase (same as n8n)
SUPABASE_URL=http://localhost:8000      # or http://kong:8000 from Docker
SUPABASE_SERVICE_KEY=<service_role_key>

# Mem0 / Postgres (same Supabase DB)
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/postgres

# Web Search
BRAVE_API_KEY=                          # optional
SEARXNG_BASE_URL=http://localhost:8080  # or http://searxng:8080 from Docker
```

## Acceptance Criteria

- [ ] Agent starts and responds to chat via Streamlit UI
- [ ] Can ingest documents from `./shared/` into Supabase pgvector
- [ ] Can retrieve relevant documents during conversation (RAG)
- [ ] Can search the web via SearXNG
- [ ] Remembers facts across conversations (Mem0 long-term memory)
- [ ] Can analyze uploaded images (vision model)
- [ ] Can execute generated Python code safely (RestrictedPython)
- [ ] All tests pass: `pytest pydantic_ai_agent/tests/`

## Next Steps

1. Review and approve this plan
2. Execute **Phase 0** (bootstrap directory + dependencies)
3. Execute **Phase 1** (core agent skeleton)
4. Continue through remaining phases

> **Note**: Each phase is independently testable. We can stop after any phase and have a working subset of functionality.

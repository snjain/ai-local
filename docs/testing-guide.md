# Local AI Packaged — Testing Guide

## Before You Start

You need these configured in your `.env` file:

```bash
cd /Users/snjain/github/ai-local
cp .env.example .env
```

Edit `.env` and set at minimum:
- `LLM_API_KEY` — OpenAI API key (or keep as `ollama` for local inference)
- `POSTGRES_PASSWORD` — Password for local Supabase Postgres
- `SUPABASE_SERVICE_KEY` — Service role key from local Supabase setup
- `DATABASE_URL` — Postgres connection string (default: `postgresql://postgres:password@127.0.0.1:5434/postgres`)
- `BRAVE_API_KEY` — Brave Search API key (optional; SearXNG runs locally)
- `JWT_SECRET` — JWT secret from local Supabase setup

Also copy and fill in `apps/agent-backend/.env` and `apps/agent-frontend/.env` if needed.

Run the SQL scripts to set up your local Supabase database:

```bash
cd /Users/snjain/github/ai-local
rav run db-setup
```

This runs all SQL files in `sql/` automatically. Alternatively, you can paste them manually into the Supabase SQL Editor at http://localhost:3000.

---

## Test 1: n8n (No API Keys Needed)

```bash
cd /Users/snjain/github/ai-local
rav run n8n
```

**Verify:**
- Open http://localhost:5678
- Complete the initial owner setup (first time only)
- Go to Workflows — you should see pre-loaded workflows

**Stop:**
```bash
rav run n8n-stop
```

---

## Test 2: Full Local Stack (Docker Compose)

```bash
cd /Users/snjain/github/ai-local
rav run up
```

**Verify all services:**
```bash
rav run ps
```

Expected output includes:
```
NAMES                    STATUS          PORTS
localai-n8n              Up ...          0.0.0.0:5678->5678/tcp
supabase-kong            Up ...          0.0.0.0:8000->8000/tcp
supabase-studio          Up ...          0.0.0.0:3000->3000/tcp
supabase-db              Up ...          0.0.0.0:5434->5432/tcp
qdrant                   Up ...          0.0.0.0:6333->6333/tcp
neo4j                    Up ...          0.0.0.0:7474->7474/tcp
searxng                  Up ...          0.0.0.0:8081->8080/tcp
...                      ...             ...
```

**Access points:**
- http://localhost:5678 — n8n
- http://localhost:8000 — Supabase API (Kong)
- http://localhost:3000 — Supabase Studio
- http://localhost:5434 — Postgres (direct)
- http://localhost:6333 — Qdrant
- http://localhost:7474 — Neo4j Browser
- http://localhost:8081 — SearXNG

**Stop:**
```bash
rav run down
```

---

## Test 3: Agent Backend — CLI Mode

```bash
cd /Users/snjain/github/ai-local/apps/agent-backend
source ../../.venv/bin/activate
python cli.py
```

**Expected interaction:**
```
==================================================
Pydantic AI Agent — CLI
Model: qwen2.5:7b-instruct-q4_K_M @ http://127.0.0.1:11434/v1
Type 'exit' or 'quit' to stop
==================================================

You: What is the capital of France?
Agent: The capital of France is Paris...

You: exit
```

**What it tests:**
- ✅ Ollama/OpenAI API connection
- ✅ Agent initialization
- ✅ Tool registration
- ✅ Mem0 memory (if configured)

---

## Test 4: Agent Backend — API Mode

Terminal 1:
```bash
cd /Users/snjain/github/ai-local/apps/agent-backend
source ../../.venv/bin/activate
rav run agent-streamlit-api
```

Terminal 2:
```bash
# Health check
curl http://localhost:8009/health

# Simple chat (no auth)
curl -X POST http://localhost:8009/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is machine learning?"}'

# Base agent chat (auth required — get token from frontend login)
curl -X POST http://localhost:8009/api/pydantic-agent \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"query": "Explain quantum computing", "user_id": "your-user-id", "request_id": "req-1"}'

# Guardrail agent
curl -X POST http://localhost:8009/api/agent-guardrail \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"query": "Explain quantum computing", "user_id": "your-user-id", "request_id": "req-2"}'

# Routing agent
curl -X POST http://localhost:8009/api/agent-routing \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"query": "Search the web for latest AI news", "user_id": "your-user-id", "request_id": "req-3"}'

# Parallel agent
curl -X POST http://localhost:8009/api/agent-parallel \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"query": "Compare Python vs JavaScript", "user_id": "your-user-id", "request_id": "req-4"}'

# Supervisor agent
curl -X POST http://localhost:8009/api/agent-supervisor \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"query": "Research climate change and summarize", "user_id": "your-user-id", "request_id": "req-5"}'
```

**Expected:** JSON response with `"response": "..."` or streamed text chunks.

---

## Test 5: Agent Backend — Streamlit UI

```bash
cd /Users/snjain/github/ai-local/apps/agent-backend
source ../../.venv/bin/activate
rav run agent-streamlit
```

**Verify:**
- Open http://localhost:8501
- Type a message and send
- Watch the agent respond

---

## Test 6: Frontend

```bash
cd /Users/snjain/github/ai-local/apps/agent-frontend
npm install  # if not done
rav run frontend
```

**Verify:**
- Open http://localhost:5173
- Sign up / Log in (uses local Supabase auth)
- Chat with the agent
- Messages render with Markdown support
- Conversation history is persisted

---

## Test 7: RAG Pipeline

```bash
# Create a test document
mkdir -p /Users/snjain/github/ai-local/shared
echo "Local AI Packaged is a self-hosted AI starter kit built with n8n, Pydantic AI, and LangGraph. It uses Ollama for local LLMs, Supabase for storage, and SearXNG for web search." > /Users/snjain/github/ai-local/shared/test_doc.txt

# Run the pipeline
rav run rag-pipeline
```

**Expected:**
```
Processing: /Users/snjain/github/ai-local/shared/test_doc.txt
  ✓ Indexed: test_doc.txt
```

**Verify in Supabase:**
```bash
rav run db-setup
```
Or manually in Supabase SQL Editor, run: `SELECT * FROM documents;`
- You should see the document chunks

Then test RAG via the agent:
```bash
curl -X POST http://localhost:8009/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Local AI Packaged?"}'
```

The agent should retrieve the document and answer based on it.

---

## Test 8: Document Ingestion API

Upload a document directly via the API:

```bash
curl -X POST http://localhost:8009/api/ingest \
  -H "Authorization: Bearer <your-jwt-token>" \
  -F "file=@/Users/snjain/github/ai-local/shared/test_doc.txt"
```

**Expected:** `{"status": "ok", ...}`

---

## Test 9: Direct Tool Endpoints

```bash
# Web search
curl -X POST http://localhost:8009/tools/web_search \
  -H "Content-Type: application/json" \
  -d '{"query": "latest AI news"}'

# RAG search
curl -X POST http://localhost:8009/tools/rag \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Local AI Packaged?"}'

# Code execution
curl -X POST http://localhost:8009/tools/code \
  -H "Content-Type: application/json" \
  -d '{"code": "print(2+2)"}'

# SQL query
curl -X POST http://localhost:8009/tools/sql \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM documents LIMIT 5"}'
```

---

## Test 10: Conversation Management

```bash
# List conversations
curl http://localhost:8009/api/conversations \
  -H "Authorization: Bearer <your-jwt-token>"

# Get messages for a conversation
curl http://localhost:8009/api/conversations/<session-id>/messages \
  -H "Authorization: Bearer <your-jwt-token>"
```

---

## Quick Smoke Test Script

Run the automated smoke test suite:

```bash
cd /Users/snjain/github/ai-local
rav run smoke-test
```

Or run this manually to verify the core backend works:

```bash
cd /Users/snjain/github/ai-local/apps/agent-backend
source ../../.venv/bin/activate

python3 << 'EOF'
import asyncio
from httpx import AsyncClient
from agent import agent, AgentDeps
from clients import get_embedding_client, get_supabase_client

async def test():
    embedding_client = get_embedding_client()
    supabase = get_supabase_client()
    
    async with AsyncClient() as http_client:
        deps = AgentDeps(
            supabase=supabase,
            embedding_client=embedding_client,
            http_client=http_client,
            brave_api_key=None,
            searxng_base_url=None,
            memories="",
        )
        result = await agent.run("Say 'Local AI Packaged is working' and nothing else.", deps=deps)
        print("Response:", result.output)

asyncio.run(test())
EOF
```

**Expected:** `Response: Local AI Packaged is working`

---

## Test 11: Admin Dashboard

With the full stack running:

```bash
rav run up
```

**Verify:**
- Open http://localhost:5173
- Log in as an admin user
- Navigate to the Admin page
- View conversations table and user management

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Need n8n secrets | Run `rav run generate-secrets` |
| `Missing credentials` / `OpenAIError` | Set `LLM_API_KEY` in `.env` (or ensure Ollama is running) |
| `supabase_url is required` | Set `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `.env` |
| `No module named 'langgraph'` | Run `uv pip install langgraph>=0.3.0` |
| `Port 5678 already in use` | `docker stop n8n` or change port |
| Frontend blank page | Check browser console for CORS errors; ensure `VITE_AGENT_ENDPOINT` is correct |
| n8n workflow not imported | Check `infra/n8n/backup/workflows/` has JSON files |
| Supabase not connecting | Ensure `rav run up` completed; check `rav run ps` |
| Postgres connection refused | Verify `DATABASE_URL` points to `127.0.0.1:5434` |
| Neo4j connection issues | Check `NEO4J_AUTH` format is `neo4j/password` |
| SearXNG returning no results | Open http://localhost:8081 and verify it's running |

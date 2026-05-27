# Local AI Packaged

A **self-hosted AI starter kit** that runs entirely on your local machine — from LLM inference to vector databases to workflow automation.

**Stack**: n8n, Supabase (Postgres + Auth + Storage), Qdrant, Neo4j, SearXNG, Langfuse, Open WebUI, Flowise, and a custom Pydantic AI agent.

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   n8n (Docker)  │────►│  Pydantic AI    │────►│   LangGraph     │
│   localhost:5678│     │  Agent (FastAPI)│     │  Multi-Agent    │
│                 │     │  localhost:8009 │     │  localhost:8009 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────┐
                    │   Local Services    │
                    │  • Ollama (LLMs)    │
                    │  • Supabase (DB)    │
                    │  • Qdrant (vectors) │
                    │  • Neo4j (graph)    │
                    │  • SearXNG (search) │
                    │  • Langfuse (obs)   │
                    └─────────────────────┘
```

---

## Quick Start

### Prerequisites

- **Python 3.12+**
- **Node.js 20+**
- **Docker / Docker Desktop**
- **uv** (`pip install uv`)
- **rav** (`pip install rav`)
- **Ollama** ([ollama.com](https://ollama.com))

### 1. Clone & Setup

```bash
cd /Users/snjain/github/ai-local

# Create virtual environment
uv venv
source .venv/bin/activate

# Install root dependencies
uv pip install -e "."

# Copy environment template
cp .env.example .env
# Edit .env with your values
```

### 2. Start Infrastructure

```bash
# Start the full local stack (Supabase, n8n, Qdrant, Neo4j, SearXNG, Langfuse, etc.)
rav run up
```

Wait for all services to be healthy:
```bash
rav run ps-ai-local
```

### 3. Database Setup

```bash
rav run db-setup
```

This runs all SQL files in `sql/` against your local Supabase Postgres instance.

### 4. Start Agent Backend

```bash
# Terminal 1: Start the agent API
rav run agent-api
```

### 5. Start RAG Pipeline

```bash
# Terminal 2: Start the document watcher
rav run rag-pipeline
```

Drop files into `shared/` to index them automatically.

### 6. Start Frontend

```bash
# Terminal 3: Start the React chat UI
cd apps/agent-frontend
npm install
rav run frontend
```

### 7. Access Services

| Service | URL | Notes |
|---------|-----|-------|
| n8n | http://localhost:5678 | Workflow automation |
| Supabase Kong | http://localhost:8000 | API gateway (requires `apikey` header) |
| Supabase Studio | http://localhost:3000 | Database studio (via docker network) |
| Agent API | http://localhost:8009 | FastAPI + Pydantic AI |
| API Docs | http://localhost:8009/docs | Auto-generated Swagger |
| Frontend | http://localhost:5173 | React chat UI |
| Streamlit UI | http://localhost:8501 | `rav run agent-streamlit` |
| SearXNG | http://localhost:8080 | Private search engine |

Services behind Caddy reverse proxy (add to `/etc/hosts`):
| Service | URL |
|---------|-----|
| Open WebUI | http://webui.localhost |
| Flowise | http://flowise.localhost |
| Langfuse | http://langfuse.localhost |
| Neo4j Browser | http://neo4j.localhost |
| Supabase | http://supabase.localhost |
| Agent (via Caddy) | http://agent.localhost |

---

## Project Structure

```
ai-local/
├── apps/
│   ├── agent-backend/          # Pydantic AI + LangGraph + FastAPI
│   │   ├── agent.py            # Main agent definition
│   │   ├── api.py              # FastAPI endpoints
│   │   ├── cli.py              # Interactive CLI
│   │   ├── streamlit_ui.py     # Streamlit chat UI
│   │   ├── config.py           # Centralized config
│   │   ├── tools/              # Agent tools (RAG, web search, code, SQL)
│   │   ├── memory/             # Mem0 long-term memory
│   │   ├── graphs/             # LangGraph architectures
│   │   └── tests/              # Pytest tests
│   ├── agent-frontend/         # React + Tailwind + shadcn/ui chat
│   │   ├── src/pages/Admin.tsx # Admin dashboard
│   │   └── src/pages/Chat.tsx  # Chat interface
│   └── rag-pipeline/           # Document ingestion pipeline
│       ├── main.py             # File watcher
│       ├── db_handler.py       # Supabase operations
│       └── text_processor.py   # Chunking + embeddings
├── infra/
│   ├── docker-compose.yml      # Full local stack
│   ├── docker-compose.n8n.yml  # Standalone n8n
│   ├── supabase/               # Supabase volume configs
│   ├── n8n/backup/workflows/   # Pre-loaded workflows
│   ├── neo4j/                  # Neo4j data/config
│   ├── searxng/                # SearXNG config
│   └── Caddyfile               # Reverse proxy
├── sql/                        # Database schema scripts
├── scripts/                    # Utility scripts (run_sql.py)
├── shared/                     # Document drop folder for RAG
├── docs/                       # Documentation & plans
├── main.py                     # Root-level RAG entrypoint
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── pyproject.toml              # uv project config
├── rav.yaml                    # Command shortcuts
└── tests/
│   └── test_smoke.py           # Smoke/integration tests
```

---

## Commands (via `rav`)

### Infrastructure
| Command | Description |
|---------|-------------|
| `rav run n8n` | Start n8n in Docker |
| `rav run n8n-stop` | Stop n8n |
| `rav run up` | Start full local stack |
| `rav run down` | Stop full stack |
| `rav run ps-ai-local` | List ai-local containers |
| `rav run ps-n8n` | List n8n containers |
| `rav run logs` | View stack logs |
| `rav run db-setup` | Run SQL setup scripts |

### Backend
| Command | Description |
|---------|-------------|
| `rav run agent-api` | Start agent API on port 8009 |
| `rav run agent-cli` | Run interactive CLI |
| `rav run agent-streamlit` | Start Streamlit chat UI |
| `rav run agent-test` | Run backend tests |
| `rav run rag-pipeline` | Start RAG file watcher |

### Frontend
| Command | Description |
|---------|-------------|
| `rav run frontend` | Start React frontend (dev mode) |
| `rav run frontend-build` | Build for production |
| `rav run frontend-install` | Install npm dependencies |

### Testing & Utilities
| Command | Description |
|---------|-------------|
| `rav run smoke-test` | Run smoke test suite |
| `rav run clean` | Destroy all containers and volumes |
| `rav run stop-all` | Stop all native + Docker services |

---

## API Endpoints

### Public (no auth)
| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `POST /chat` | Simple chat with automatic RAG |
| `POST /chat/stream` | Streaming chat (SSE) |
| `POST /tools/web_search` | Direct web search |
| `POST /tools/rag` | Direct RAG search |
| `POST /tools/code` | Execute Python code |
| `POST /tools/sql` | Execute SQL query |

### Auth Required (Bearer JWT)
| Endpoint | Description |
|----------|-------------|
| `POST /api/pydantic-agent` | Full agent with auth + history + streaming |
| `POST /api/agent-routing` | LLM routing architecture |
| `POST /api/agent-parallel` | Parallel agents |
| `POST /api/agent-supervisor` | Supervisor delegation |
| `POST /api/agent-guardrail` | Guardrail validation |
| `GET /api/conversations` | List conversations |
| `GET /api/conversations/{id}/messages` | Get conversation messages |
| `POST /api/ingest` | Upload document for RAG |

Generate a local JWT for testing:
```bash
export AI_LOCAL_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJsb2NhbC11c2VyLTEyMyIsInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYXVkIjoiYXV0aGVudGljYXRlZCIsImVtYWlsIjoidGVzdEB0ZXN0LmNvbSJ9..."
```

---

## RAG Pipeline

Documents dropped into `shared/` are automatically:
1. Chunked by the RAG pipeline
2. Embedded using your configured embedding model
3. Stored in Supabase `documents` table with pgvector

The chat endpoints automatically retrieve relevant documents and prepend them to the agent's context.

Upload via API:
```bash
curl -X POST http://localhost:8009/api/ingest \
  -H "Authorization: Bearer $AI_LOCAL_TOKEN" \
  -F "file=@/path/to/document.pdf"
```

---

## Testing

See [`docs/testing-guide.md`](docs/testing-guide.md) for a comprehensive testing guide.

### Run all tests
```bash
pytest -v
```

### Smoke tests
```bash
rav run smoke-test
```

### Backend tests
```bash
rav run agent-test
```

### Code coverage
```bash
rav run coverage
```

Generates a terminal report and an HTML report in `htmlcov/`. Current coverage: ~60%.

---

## Development Phases

1. **Phase 1**: Local infrastructure (Docker Compose) ✅
2. **Phase 2**: Pydantic AI agent backend ✅
3. **Phase 3**: RAG document pipeline ✅
4. **Phase 4**: React frontend ✅
5. **Phase 5**: LangGraph multi-agent architectures ✅
6. **Phase 6**: Admin dashboard & observability ✅
7. **Phase 7**: Documentation & polish ✅

---

## License

Proprietary — see reference projects for component licenses.

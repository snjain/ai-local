# Plan: Mirror and Setup n8n from Local AI Packaged (macOS Only)

## Goal
Start from a **clean Docker state**, then progressively mirror the `/Users/snjain/Downloads/dyn/local-ai-packaged` directory into `/Users/snjain/github/ai` — one module at a time, beginning with n8n. The setup must be **fully reproducible**: any container can be destroyed and recreated on demand from the mirrored files.

> **Immediate post-approval action (before any execution):** Save this plan to `/Users/snjain/github/ai/docs/plan-n8n-setup.md` so it is preserved in the project for reference during execution.

## Context
The source directory is a full **Local AI Packaged** stack. This plan ensures a clean start, then copies and activates one module per phase. Each phase is independently runnable and reproducible.

> This project is set up as a self-contained Python project using **`uv`** for virtual environment management and **`rav`** for command shortcuts. All commands below are also available via `rav run <command>` — see `rav.yaml` for the full list.
>
> ```bash
> # Activate the virtual environment
> source .venv/bin/activate
>
> # List all available shortcuts
> rav list
>
> # Example: run Phase 0 cleanup
> rav run clean
>
> # Example: start n8n only
> rav run n8n
> ```

---

## Pre-Phase 0: Reconstructability Confirmation

**Can we reconstruct all containers from `/Users/snjain/Downloads/dyn/local-ai-packaged`?**

### YES — with the following verification:

| Requirement | Source Status |
|-------------|---------------|
| **Service definitions** | `docker-compose.yml` defines n8n, Qdrant, Neo4j, Caddy, Langfuse, SearXNG, Flowise, Open WebUI, Redis, ClickHouse, MinIO, Postgres |
| **Supabase stack** | `start_services.py` auto-clones `https://github.com/supabase/supabase.git` and uses `supabase/docker/docker-compose.yml` |
| **n8n workflows** | `n8n/backup/workflows/` contains pre-exported workflows; `n8n/backup/credentials/` contains credentials |
| **Service configs** | `searxng/`, `neo4j/`, `flowise/`, `caddy-addon/`, `Caddyfile` are all present |
| **Environment secrets** | `.env.example` has the template structure; the actual `.env` in source has real secrets |
| **Orchestration** | `start_services.py` handles Supabase cloning, env copying, SearXNG key generation, and startup ordering |

### What will be lost when wiping
- **Docker volumes** (`n8n_storage`, `langfuse_postgres_data`, `qdrant_storage`, etc.) — any data created after the initial workflow import
- **Running container state** — but this is intentional since we want a fresh start

### What will be preserved (if copied)
- **n8n workflows** from `n8n/backup/workflows/`
- **Credentials** from `n8n/backup/credentials/`
- **Service configurations** (Caddyfile, searxng settings, neo4j config, etc.)

### Recommendation
Copy the source's actual `.env` file (not just `.env.example`) so that secrets match and re-created services connect correctly without re-configuration. Alternatively, generate fresh secrets and re-create credentials manually in n8n after startup.

---

## Phase 0: Clean Docker State (One-Time)

Before mirroring anything, ensure Docker is clean of any stale containers, volumes, or networks from previous runs.

### 0A — Stop and remove existing project containers
```bash
# Stop and remove any existing 'localai' project containers (macOS: always use --profile none)
docker compose -p localai -f docker-compose.yml --profile none down --volumes --remove-orphans 2>/dev/null || true

# Also remove any individual n8n containers from Phase 1
docker compose -f docker-compose.n8n.yml down --volumes 2>/dev/null || true
```

### 0B — Remove project images
Since we are recreating containers from the ground up, remove all images used by the stack so they are freshly pulled:

```bash
# Remove all project-related images (safe to run even if some are already gone)
docker rmi -f \
  n8nio/n8n:latest \
  searxng/searxng:latest \
  ollama/ollama:latest \
  postgres:17 \
  langfuse/langfuse:3 \
  langfuse/langfuse-worker:3 \
  caddy:2-alpine \
  qdrant/qdrant:latest \
  ghcr.io/open-webui/open-webui:main \
  neo4j:latest \
  clickhouse/clickhouse-server:latest \
  valkey/valkey:8-alpine \
  flowiseai/flowise:latest \
  minio/minio:latest \
  kong/kong:3.9.1 \
  postgrest/postgrest:v14.8 \
  timberio/vector:0.53.0-alpine \
  supabase/studio:2026.04.27-sha-5f60601 \
  supabase/storage-api:v1.48.26 \
  supabase/postgres-meta:v0.96.3 \
  supabase/logflare:1.36.1 \
  supabase/edge-runtime:v1.71.2 \
  supabase/realtime:v2.76.5 \
  supabase/gotrue:v2.186.0 \
  supabase/supavisor:2.7.4 \
  darthsim/imgproxy:v3.30.1 \
  supabase/postgres:15.8.1.085 \
  2>/dev/null || true
```

### 0C — Prune unused Docker resources
```bash
# Remove stopped containers, unused networks, dangling images, and build cache
docker system prune -f

# Remove ALL unused volumes (be careful if you have other projects):
docker volume prune -f
```

### 0D — Verify clean state
```bash
docker ps -a
docker volume ls
docker images
```

> **Safety note:** This only removes containers/volumes managed by this project's compose files. Other Docker workloads are unaffected.

---

## Phase 1: n8n Only (SQLite, No Supabase)

### What to copy from source
- `n8n/` directory (pre-built workflows & credentials)
- `shared/` directory (shared volume mount)
- `.env` (or `.env.example` → `.env`) for `N8N_ENCRYPTION_KEY` and `N8N_USER_MANAGEMENT_JWT_SECRET`

### What to create
A minimal `docker-compose.n8n.yml` that runs **only** n8n with its internal SQLite database:

```yaml
services:
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - N8N_USER_MANAGEMENT_JWT_SECRET=${N8N_USER_MANAGEMENT_JWT_SECRET}
      - N8N_DIAGNOSTICS_ENABLED=false
      - N8N_PERSONALIZATION_ENABLED=false
    volumes:
      - n8n_storage:/home/node/.n8n
      - ./n8n/backup:/backup
      - ./shared:/data/shared
    entrypoint: /bin/sh
    command: -c "n8n import:credentials --separate --input=/backup/credentials 2>/dev/null || true; n8n import:workflow --separate --input=/backup/workflows 2>/dev/null || true; n8n start"

volumes:
  n8n_storage:
```

### Run
```bash
docker compose -f docker-compose.n8n.yml up -d
```

n8n will be at `http://localhost:5678`.

### Reproducibility
To destroy and recreate n8n at any time:
```bash
docker compose -f docker-compose.n8n.yml down --volumes
docker compose -f docker-compose.n8n.yml up -d
```

---

## Phase 2: Add Supabase + Switch n8n to Postgres

### What to copy from source
- `supabase/` (if not already cloned by `start_services.py`)
- `start_services.py`
- `docker-compose.yml` (the full one from source)
- `docker-compose.override.private.yml`

### What changes
- n8n is reconfigured to use Supabase Postgres (`db` host) instead of SQLite.
- The full `docker-compose.yml` is brought in, but we still **only start n8n + Supabase**.

### Pre-step: Stop Phase 1 n8n
```bash
docker compose -f docker-compose.n8n.yml down
```

### Run
```bash
# Use the full compose, but start only n8n and its dependencies (macOS: no GPU profile)
docker compose -p localai -f docker-compose.yml up -d n8n
```

This automatically brings up `n8n-import` and Supabase `db`.

### Reproducibility
To destroy and recreate n8n + Supabase:
```bash
docker compose -p localai -f docker-compose.yml down --volumes --remove-orphans
docker compose -p localai -f docker-compose.yml up -d n8n
```

---

## Phase 3: Add Qdrant

### What to copy from source
Nothing new to copy — Qdrant is defined in `docker-compose.yml` with a Docker volume only.

### Run
```bash
docker compose -p localai -f docker-compose.yml up -d qdrant
```

### Reproducibility
To recreate Qdrant alone:
```bash
docker compose -p localai -f docker-compose.yml rm -sf qdrant
docker compose -p localai -f docker-compose.yml up -d qdrant
```

---

## Phase 4: Add Open WebUI + Flowise

### What to copy from source
- `flowise/` directory

### Run
```bash
docker compose -p localai -f docker-compose.yml up -d open-webui flowise
```

---

## Phase 5: Add Neo4j + SearXNG

### What to copy from source
- `neo4j/` directory
- `searxng/` directory
- `Caddyfile`
- `caddy-addon/` directory

### Run
```bash
docker compose -p localai -f docker-compose.yml up -d neo4j searxng
```

---

## Phase 6: Add Langfuse

### What to copy from source
Nothing new — Langfuse services are fully defined in `docker-compose.yml`.

### Run
```bash
docker compose -p localai -f docker-compose.yml up -d langfuse-worker langfuse-web
```

---

## Phase 7: Add Caddy + Full Stack Convergence

### What to copy from source
All remaining files (`assets/`, `n8n-tool-workflows/`, `n8n_pipe.py`, `Local_RAG_AI_Agent_n8n_Workflow.json`, `README.md`, `LICENSE`).

### Run
```bash
# Start the remaining service
docker compose -p localai -f docker-compose.yml up -d caddy

# Or switch to unified orchestration for daily use (macOS: always --profile none):
python start_services.py --profile none --environment private
```

At this point, the working directory is a **complete mirror** of the source.

---

## Phase 8: Verify n8n

1. Check container health: `docker ps --format "table {{.Names}}\t{{.Status}}"`
2. Open `http://localhost:5678` and complete the initial owner setup.
3. Verify pre-imported workflows from `n8n/backup/workflows/` are present.
4. Create credentials for local services as needed:
   - Postgres (Supabase): host=`db`, port=`5432`, user=`postgres`, password from `.env`
   - Qdrant: URL=`http://qdrant:6333` (no API key locally)

---

## Master Reproducibility Cheat Sheet (macOS)

At any point, you can fully destroy and recreate the entire stack:

```bash
# Destroy everything (containers + volumes)
docker compose -p localai -f docker-compose.yml --profile none down --volumes --remove-orphans

# Recreate everything (macOS: always --profile none since GPU passthrough is unavailable)
python start_services.py --profile none --environment private
```

Or recreate individual modules:

```bash
# Recreate only n8n + its dependencies
docker compose -p localai -f docker-compose.yml up -d --force-recreate n8n

# Recreate only Qdrant
docker compose -p localai -f docker-compose.yml up -d --force-recreate qdrant
```

---

## Summary of Files Copied Per Phase

| Phase | Directories / Files Copied | New Service(s) |
|-------|---------------------------|----------------|
| 0 | — | Docker cleanup |
| 1 | `n8n/`, `shared/`, `.env` | n8n (SQLite) |
| 2 | `supabase/`, `start_services.py`, `docker-compose.yml`, `docker-compose.override.*.yml` | Supabase Postgres |
| 3 | — | Qdrant |
| 4 | `flowise/` | Open WebUI, Flowise |
| 5 | `neo4j/`, `searxng/`, `Caddyfile`, `caddy-addon/` | Neo4j, SearXNG |
| 6 | — | Langfuse (ClickHouse, MinIO, Redis, Postgres) |
| 7 | `assets/`, `n8n-tool-workflows/`, `n8n_pipe.py`, etc. | Caddy |
| 8 | — | Full stack validation |

---

## Service Dependency Diagram

Based on the `docker-compose.yml` from the source, services have the following dependency chain:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         n8n Core Chain                                  │
│                                                                         │
│   n8n  ──depends_on──►  n8n-import  ──depends_on──►  db (Supabase)    │
│  (app)                  (one-shot importer)            (Postgres)       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      Langfuse Observability Chain                       │
│                                                                         │
│   langfuse-web  ──┐                                                     │
│   langfuse-worker └──►  postgres  ◄──┐                                  │
│                        clickhouse    ├── all must be healthy            │
│                        minio         │                                  │
│                        redis      ◄──┘                                  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     Independent Services                                │
│                                                                         │
│   qdrant    neo4j    searxng    flowise    open-webui    caddy          │
│  (vector)  (graph)   (search)   (agents)    (chat UI)   (proxy)       │
│                                                                         │
│   No hard dependencies. Can be started/stopped individually.            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Startup Order Implications

1. **Supabase `db` must be healthy before n8n can start** (via `n8n-import`).
2. **Langfuse services must wait for all four backing stores** (Postgres, ClickHouse, MinIO, Redis).
3. **All other services** (Qdrant, Neo4j, SearXNG, Flowise, Open WebUI, Caddy) can start in any order.

This is why the phased rollout in this plan respects these chains:
- Phase 2 brings up `db` before n8n.
- Phase 6 brings up the entire Langfuse dependency graph at once.
- Phases 3–5 and 7 add independent services incrementally.

---

## About `--profile none` on macOS

The source `docker-compose.yml` includes an **Ollama** service (local LLM inference) that is conditionally enabled via Docker Compose profiles. On macOS, **only `--profile none` is valid**.

### Why macOS cannot use GPU profiles

Docker Desktop on macOS runs inside a Linux VM and **cannot passthrough Apple Silicon or Intel GPUs** to containers. The `gpu-nvidia` and `gpu-amd` profiles are non-functional on macOS. The `cpu` profile works but is very slow compared to native execution.

### Why `--profile none` is the correct choice

| Profile | macOS Support | Reason |
|---------|---------------|--------|
| `none` | ✅ **Yes** | Ollama runs **outside** Docker, using macOS native Metal GPU acceleration. |
| `cpu` | ⚠️ Works but avoid | Ollama runs in Docker with CPU-only inference — very slow. |
| `gpu-nvidia` | ❌ No | Requires NVIDIA GPU + nvidia-docker, unavailable on macOS. |
| `gpu-amd` | ❌ No | Requires AMD GPU + `/dev/dri`, unavailable on macOS. |

### Running Ollama natively on macOS (recommended)

```bash
# Install Ollama
brew install ollama

# Start Ollama
ollama serve

# Pull a model (e.g., Llama 3.1)
ollama pull llama3.1
```

Then in n8n, configure the Ollama credential with:
- **Base URL**: `http://host.docker.internal:11434`

## macOS Notes

- **GPU**: `--profile none` is required because Docker Desktop on macOS cannot passthrough Apple Silicon or Intel GPUs to containers.
- **Ollama**: If local LLM inference is needed, run Ollama natively on macOS (install via `brew install ollama` or download from ollama.com) and point n8n to `http://host.docker.internal:11434`.
- **SearXNG first-run**: `start_services.py` auto-handles the `cap_drop` temporary relaxation on macOS.
- **Port conflicts**: Verify ports `5678` (n8n), `5432` (Postgres), etc. are free before starting.

"""Smoke tests for the Local AI Packaged stack.

Run with:
    pytest test_all.py -v
    pytest test_all.py -v -k health   # only health checks
    pytest test_all.py -v --tb=short  # shorter tracebacks
"""

import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python3"
BACKEND_DIR = PROJECT_ROOT / "apps" / "agent-backend"
RAG_DIR = PROJECT_ROOT / "apps" / "rag-pipeline"
FRONTEND_DIR = PROJECT_ROOT / "apps" / "agent-frontend"
INFRA_DIR = PROJECT_ROOT / "infra"
ANON_KEY = os.getenv(
    "ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIiwiaWF0IjoxNzc4OTkwNDAwLCJleHAiOjE5MzY3NTY4MDB9.UIu301iB3XGhh7F2VLlwiQf6MAsElsNL_sREjGXDD1o",
)


def _run(cmd: str | list, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    if isinstance(cmd, list):
        return subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, capture_output=True, text=True)
    return subprocess.run(cmd, shell=True, cwd=cwd or PROJECT_ROOT, capture_output=True, text=True)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Python Syntax
# ──────────────────────────────────────────────────────────────────────────────

def test_python_syntax_backend():
    """All backend Python files compile without syntax errors."""
    result = _run("find apps/agent-backend -name '*.py' -exec python3 -m py_compile {} +")
    assert result.returncode == 0, result.stderr


def test_python_syntax_rag():
    """All RAG pipeline Python files compile without syntax errors."""
    result = _run("find apps/rag-pipeline -name '*.py' -exec python3 -m py_compile {} +")
    assert result.returncode == 0, result.stderr


# ──────────────────────────────────────────────────────────────────────────────
# 2. Backend Module Imports
# ──────────────────────────────────────────────────────────────────────────────

BACKEND_IMPORTS = [
    ("config", "import config"),
    ("deps", "import deps"),
    ("clients", "import clients"),
    ("agent", "import agent"),
    ("api", "import api"),
    ("tools.web_search", "from tools import web_search"),
    ("tools.rag_search", "from tools import rag_search"),
    ("tools.code_execution", "from tools import code_execution"),
    ("tools.image_analysis", "from tools import image_analysis"),
    ("tools.sql_query", "from tools import sql_query"),
    ("graphs.state", "from graphs import state"),
    ("graphs.utils", "from graphs import utils"),
    ("graphs.patterns", "from graphs import patterns"),
    ("graphs.routing_graph", "from graphs import routing_graph"),
    ("graphs.guardrail_graph", "from graphs import guardrail_graph"),
    ("graphs.parallel_graph", "from graphs import parallel_graph"),
    ("graphs.supervisor_graph", "from graphs import supervisor_graph"),
]


@pytest.mark.parametrize("name,imp", BACKEND_IMPORTS)
def test_backend_import(name: str, imp: str):
    """Backend module {name} imports successfully."""
    python = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"
    result = _run(f'{python} -c "{imp}"', cwd=BACKEND_DIR)
    assert result.returncode == 0, f"Failed to import {name}: {result.stderr}"


# ──────────────────────────────────────────────────────────────────────────────
# 3. RAG Pipeline Imports
# ──────────────────────────────────────────────────────────────────────────────

RAG_MODULES = ["text_processor", "db_handler", "main"]


@pytest.mark.parametrize("mod", RAG_MODULES)
def test_rag_import(mod: str):
    """RAG module {mod} imports successfully."""
    python = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"
    result = _run(f'{python} -c "import {mod}"', cwd=RAG_DIR)
    assert result.returncode == 0, f"Failed to import {mod}: {result.stderr}"


# ──────────────────────────────────────────────────────────────────────────────
# 4. Service Health Checks
# ──────────────────────────────────────────────────────────────────────────────

def test_n8n_health():
    """n8n responds with HTTP 200."""
    result = _run("curl -s -o /dev/null -w '%{http_code}' http://localhost:5678")
    status = result.stdout.strip()
    if status != "200":
        pytest.skip(f"n8n not running (status: {status}). Run: rav run n8n")


def test_supabase_health():
    """Supabase REST API responds with HTTP 200."""
    result = _run(
        f"curl -s -o /dev/null -w '%{{http_code}}' -H 'apikey: {ANON_KEY}' http://localhost:8000/rest/v1/"
    )
    status = result.stdout.strip()
    if status not in ("200", "404"):
        pytest.skip(f"Supabase not running (status: {status}). Run: rav run up")


# ──────────────────────────────────────────────────────────────────────────────
# 5. Frontend Build
# ──────────────────────────────────────────────────────────────────────────────

def test_frontend_build():
    """Frontend builds successfully for production."""
    result = _run("npm run build 2>&1", cwd=FRONTEND_DIR)
    assert "built in" in result.stdout or result.returncode == 0, (
        f"Frontend build failed:\n{result.stdout}\n{result.stderr}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# 6. Docker Compose Validation
# ──────────────────────────────────────────────────────────────────────────────

def test_docker_compose_main_valid():
    """infra/docker-compose.yml is syntactically valid."""
    result = _run("docker compose -f docker-compose.yml config > /dev/null", cwd=INFRA_DIR)
    assert result.returncode == 0, f"docker-compose.yml invalid:\n{result.stderr}"


def test_docker_compose_n8n_valid():
    """infra/docker-compose.n8n.yml is syntactically valid."""
    result = _run("docker compose -f docker-compose.n8n.yml config > /dev/null", cwd=INFRA_DIR)
    assert result.returncode == 0, f"docker-compose.n8n.yml invalid:\n{result.stderr}"

# Agent Architectures (Module 7)

This package implements the multi-agent architecture patterns from AI Agent Mastery Module 7 using **LangGraph** for orchestration and **Pydantic AI** for agent execution.

## Architecture: LangGraph Orchestrates, Pydantic AI Executes

```
LangGraph StateGraph (orchestration layer)
    ├── Nodes: Pydantic AI agents (reasoning + tool execution)
    ├── Edges: Conditional routing logic
    └── Streaming: astream() with custom writer() calls
```

## Implemented Patterns

All workflows live in `graphs/` and expose compiled workflows + initial state factories.

### 1. LLM Routing (`graphs/routing_graph.py`)
**Pattern**: START → Router Node → [Conditional] → Specialized Agent → END

A lightweight router agent classifies the query, then LangGraph conditionally routes to:
- `web_search` — Current events, general knowledge
- `rag_search` — Document/knowledge base queries  
- `code_execution` — Programming, data analysis
- `sql_query` — Database queries
- `fallback` — Greetings, small talk, ambiguous queries

**Endpoint**: `POST /api/agent-routing`

### 2. Parallel Agents (`graphs/parallel_graph.py`)
**Pattern**: START → [Parallel: Web | RAG | Code] → Synthesis → END

Runs three research agents simultaneously via parallel graph nodes:
- **Web Research Agent** — Searches the web
- **Document Research Agent** — Searches knowledge base (RAG)
- **Analytics Agent** — Executes Python code

A synthesis agent combines all findings into a coherent response.

**Endpoint**: `POST /api/agent-parallel`

### 3. Supervisor Agent (`graphs/supervisor_graph.py`)
**Pattern**: START → Supervisor → [Sub-Agent → Supervisor]* → Final Response → END

A supervisor agent iteratively analyzes the query and accumulated context:
1. Decides whether to delegate or respond directly
2. If delegating, provides a specific task
3. Sub-agent executes and appends summary to shared state
4. Supervisor re-evaluates with new context
5. Up to 5 iterations before forcing final response

**Endpoint**: `POST /api/agent-supervisor`

### 4. Guardrail Agent (`graphs/guardrail_graph.py`)
**Pattern**: START → Primary Agent → Guardrail → [Valid? END] : [Feedback → Primary Agent]

A two-agent validation system with up to 3 correction iterations:
1. **Primary Agent** generates a response
2. **Guardrail Agent** validates for accuracy, citations, relevance, safety
3. If invalid, feedback is injected into the primary agent's system prompt
4. After 3 failed attempts, fallback node returns best-effort response

**Endpoint**: `POST /api/agent-guardrail`

## Key Design Patterns

### Streaming Inside Nodes
Each LangGraph node receives a `writer` callback. Pydantic AI agents stream tokens via `.iter()`:

```python
async with agent.iter(input, deps=deps) as run:
    async for node in run:
        if agent.is_model_request_node(node):
            async with node.stream(run.ctx) as stream:
                async for event in stream:
                    if isinstance(event, PartStartEvent):
                        writer(event.part.content)
                    elif isinstance(event, PartDeltaEvent):
                        writer(event.delta.content_delta)
```

### API Streaming
The API uses LangGraph's `astream(..., stream_mode=["custom", "values"])`:
- `"custom"` — streams `writer()` calls from nodes in real-time
- `"values"` — captures final state for metadata

### State Management
All states extend `BaseAgentState` (TypedDict) and carry:
- `query`, `session_id`, `request_id`
- `pydantic_message_history` — conversation context for Pydantic AI agents
- `final_response` — accumulated output

## Reference Patterns (`architectures/patterns.py`)

Implements the two fundamental collaboration patterns from Module 7.3:
1. **Agent-as-Tool** — One agent invokes another as a `@tool`
2. **Agent Handoff** — Union output types for control transfer

These are standalone examples for learning, not wired to endpoints.

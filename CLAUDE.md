# CLAUDE.md - Project Context for Claude Code

## Project Overview
LabZ is a multi-agent strategic advisory platform. Users ask business strategy questions, and a team of AI agents collaborates to produce comprehensive analysis with visualizations, citations, and follow-up suggestions.

## Tech Stack
- **Backend**: FastAPI (Python), SQLAlchemy ORM, PostgreSQL (prod) / SQLite (dev/test)
- **Frontend**: React + TypeScript, Chakra UI, React Query, Vite
- **AI**: Custom multi-agent framework using OpenAI function calling (NOT LangChain/CrewAI)
- **LLM Providers**: OpenAI (GPT-4o, GPT-4o-mini) + Google Gemini

## Architecture

### Agent System
Custom-built multi-agent orchestration at `backend/src/agents/`:
- **Director** (`config/director.yaml`): Routes queries to specialists, validates info sufficiency
- **Specialists**: business_sme, market_research, competitive_intel, customer_intel, financial, risk, ip_expert, devils_advocate, research_librarian
- **Synthesizer** (`config/synthesizer.yaml`): Composes final response from all specialist outputs
- **Custom Agents**: User-created agents stored in DB, registered at runtime

Flow: User Query → Director → Specialist Agents (parallel) → Synthesizer → Response

Key files:
- `backend/src/agents/base.py` — Agent class with OpenAI function calling, execution tracing (~720 lines)
- `backend/src/agents/crew.py` — Crew orchestrator (~210 lines)
- `backend/src/agents/registry.py` — Loads agents from YAML configs
- `backend/src/agents/tools/` — 15+ tools (web_search, calculator, visualizer, image_generator, etc.)
- `backend/src/agents/trace_summarizer.py` — Summarizes execution traces for follow-up context

### Execution Trace (Network Graph)
Every query produces an `ExecutionTrace` (nodes + edges) showing which agents and tools were used:
- Node types: `query`, `context`, `agent`, `tool`, `response`
- Stored in `ChatQuery.execution_trace` (JSON column)
- Streamed in real-time via SSE (`trace_update` events)
- Rendered with ECharts in `frontend/src/components/ExecutionGraph.tsx`

### API Endpoints
- `POST /api/llm/chat/stream` — Main streaming chat endpoint (SSE)
- `POST /api/llm/chat` — Non-streaming chat endpoint
- `GET /api/threads/{id}/queries` — Fetch thread messages
- SSE event types: `trace_update`, `progress_update`, `thread_created`, `response`, `done`, `error`

### Data Models (`backend/src/models.py`)
- **User**: email, username, password_hash, is_admin
- **Organization**: name, description, org_metadata (JSON: industry, type, purpose, goals)
- **Thread**: user_id, org_id, thread_metadata, selected_agent_ids, default_answer_mode
- **ChatQuery**: message, response, execution_trace, content_structure, followup_questions, answer_mode, reask_of_query_id, followup_of_query_id, agent_ids_used

### Frontend Structure
- `frontend/src/pages/Chat.tsx` — Main chat page with streaming, has its own `sendMessageStream` wrapper
- `frontend/src/services/api.ts` — API client with types
- `frontend/src/components/FollowUpSuggestions.tsx` — Two categories: Related (purple) + Deep Dive (teal)
- `frontend/src/components/ExecutionGraph.tsx` — Network graph visualization
- `frontend/src/features/chat/hooks/useMessageStream.ts` — Streaming hook (used elsewhere, Chat.tsx has its own implementation)

## Key Conventions
- **Migrations**: `backend/alembic/versions/` — always check column existence before adding
- **LLM Client**: `backend/src/llm_client.py` — abstraction supporting OpenAI + Gemini; agents can override model in YAML
- **Agent configs**: YAML files in `backend/src/agents/config/` with system_prompt, tools, can_delegate_to
- **Answer modes**: SUMMARY, LIGHT, EXTENDED, PROJECT_PLAN, ROADMAP — control response verbosity
- **Follow-up questions**: Two types — `related` (new angles) and `deep_dive` (builds on parent analysis via followup_of_query_id)
- **Schemas**: `backend/src/schemas.py` — Pydantic models for API request/response
- **CRUD**: `backend/src/crud/` — database operations per entity

## Testing
- Backend: `backend/tests/` with pytest, SQLite in-memory DB
- Frontend: `frontend/src/tests/` with Vitest
- Note: conftest.py imports the app which requires env vars (OPENAI_API_KEY, GEMINI_API_KEY)

## Common Tasks
- Adding a new agent: Create YAML in `backend/src/agents/config/`, add to director's `can_delegate_to`
- Adding a new tool: Add to `backend/src/agents/tools/`, register in `__init__.py`
- Database changes: Add column to models.py, create migration in alembic/versions/, update schemas.py and crud/

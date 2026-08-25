# LabZ

A modern full-stack application with React frontend, FastAPI backend, PostgreSQL database, and LLM integration capabilities.

## 🏗️ Architecture

- **Frontend**: React + TypeScript + Vite
- **Backend**: Python + FastAPI
- **Database**: PostgreSQL
- **LLM Integration**: Multi-provider support (OpenAI, Google Gemini) with per-agent model selection
- **Agentic Framework**: CrewAI-inspired multi-agent system with specialized agents
- **Vector Store**: ChromaDB for semantic document search
- **Containerization**: Docker & Docker Compose
- **Monorepo**: Single repository for easier development and deployment

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose installed
- An LLM key: `GEMINI_API_KEY` and/or `OPENAI_API_KEY` (OpenAI as fallback is strongly recommended)
- Python 3.11+ and Node.js 20+ only if you run without Docker

### Demo (recommended)

Loads the validated **Technical Due Diligence** configuration, then starts the stack:

```bash
cp .env.example .env   # add GEMINI_API_KEY and/or OPENAI_API_KEY
./scripts/demo.sh
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:3001

Register, create a workspace, and open Chat. The top bar should read **Technical Due
Diligence**. Upload or summarize architecture, dependency, security, or reliability evidence,
then watch the specialist execution graph.

Public crew catalog (roles, tools, output contracts, and sample prompts): see the Lab Z site
`/crews` page.

Select another bundled example by directory name:

```bash
./scripts/demo.sh business-coaching-crew
```

Stop with Ctrl-C, then `docker compose down` if you want to tear down containers.

### Running with Docker (built-in Business Strategy crew)

If you skip `demo.sh` and just run Compose, Zero uses the built-in **Business Strategy** roster:

```bash
cp .env.example .env   # add keys
docker compose up --build
```

Load a different crew later:

```bash
./scripts/load-crew.sh --restart ./backend/crews/examples/technical-due-diligence
./scripts/load-crew.sh --restart --default   # back to Business Strategy
```

### Local Development (Without Docker)

1. **Start PostgreSQL:**
   ```bash
   docker-compose up postgres -d
   ```

2. **Backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp env.example .env
   uvicorn src.main:app --reload --port 3001
   ```

3. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## 📁 Project Structure

```
LabZ/
├── frontend/          # React frontend application
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── backend/           # Python/FastAPI backend
│   ├── src/
│   │   ├── database.py  # Database connection
│   │   ├── models.py    # SQLAlchemy models
│   │   ├── schemas.py   # Pydantic schemas
│   │   ├── crud.py      # Database operations
│   │   └── main.py      # FastAPI app
│   ├── alembic/         # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml # Docker Compose configuration
└── README.md
```

## 🔧 Configuration

### Environment Variables

**Backend** (`backend/.env`):
- `PORT`: Backend server port (default: 3001)
- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: OpenAI API key (required for OpenAI models)
- `GOOGLE_API_KEY` or `GEMINI_API_KEY`: Google Gemini API key (required for Gemini models)
- `LLM_MODEL`: Default LLM model (default: `gpt-4o`). Examples: `gpt-4o`, `gpt-4o-mini`, `gemini-3-pro-preview`, `gemini-flash-latest`
- `LLM_PROVIDER`: LLM provider (optional, auto-detected from model name if not set)
- `CHROMA_PERSIST_DIR`: Directory for ChromaDB vector store (default: `./chroma_db`)
- `OPENAI_TPM_LIMIT`: Tokens per minute limit for rate limiting (default: `30000`)
- `OPENAI_RPM_LIMIT`: Requests per minute limit for rate limiting (optional, no default)

**Frontend** (`frontend/.env`):
- `VITE_API_URL`: Backend API URL (default: http://localhost:3001)

## ☁️ Cloud Deployment

**Recommended Setup:** Vercel (Frontend) + Railway (Backend + Database)

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions.

**Quick Summary:**
- **Frontend:** Deploy to Vercel (free) - optimized for React/Vite
- **Backend:** Deploy to Railway ($5/month) - includes Postgres, easy Docker deployment
- **Total Cost:** ~$5/month

### Other Deployment Options

- **Render:** Alternative to Railway, free tier available (spins down after inactivity)
- **Fly.io:** Can host everything, free tier available
- **All-in-one:** Railway or Render can host frontend too, but Vercel is better for React apps

## 🛠️ Development

### Agentic Architecture

LabZ uses a multi-agent system inspired by CrewAI, where specialized agents collaborate to provide comprehensive strategic analysis:

- **Strategic Director**: Orchestrates specialist agents and coordinates the workflow
- **Business SME**: Provides organizational context from knowledge base
- **Customer Intelligence**: Deep customer analysis and personas
- **Market Research**: Market trends and industry data
- **Competitive Intelligence**: Competitor analysis
- **Financial Analyst**: Financial calculations and projections
- **Risk Assessment**: Strategic risk evaluation
- **Intellectual Property Expert**: IP strategy, protection, and risk assessment
- **Devil's Advocate**: Critical evaluation and risk identification
- **Research Librarian**: Source discovery and citation management
- **Strategy Synthesizer**: Combines all insights into final recommendations

#### Building your own crew with CrewDefine

[CrewDefine](https://github.com/lab-zee/CrewDefine) is the companion CLI for authoring new crews. It runs a guided LLM interview and emits a ready-to-drop-in directory:

```bash
# 1. Author (separate step — typically 5–15 min)
crewdefine new

# 2. Load into this repo (~30 sec)
./scripts/load-crew.sh ../CrewDefine/crews/my-crew

# 3. Restart backend
docker compose restart backend
```

- `crews/<name>/agents/*.yaml` → copied to `backend/crews/active/agents/` via `load-crew.sh`
- `crews/<name>/tools/*.py` → copied to `backend/crews/active/tools/` (auto-discovered on startup)
- Revert to the built-in LabZ strategy crew: `./scripts/load-crew.sh --default`

Convention: keep the orchestrator agent IDs as `director` and `synthesizer` — the registry looks them up by name.

See [`backend/src/agents/tools/plugins/README.md`](./backend/src/agents/tools/plugins/README.md) for the plugin tool contract.

### LLM Model Configuration

The system supports per-agent model selection for cost and performance optimization:

**Default Model (Environment Variable):**
- Set `LLM_MODEL` in `backend/.env` (default: `gpt-4o`)
- This is the default model used by all agents unless overridden

**Per-Agent Model Override:**
- Uncomment and set the `model` field in agent YAML configs (`backend/src/agents/config/*.yaml`)
- Example: `model: gemini-flash-latest` in `synthesizer.yaml`

**Model Resolution Priority:**
1. Agent YAML config `model` field (if uncommented)
2. `LLM_MODEL` environment variable
3. Default: `gpt-4o`

**Recommended Cost Optimization:**
- **Director**: `gemini-3-pro-preview` ($2/$12) - Complex orchestration
- **Synthesizer**: `gemini-flash-latest` ($0.30/$2.50) - Text synthesis
- **Specialist Agents**: `gemini-flash-latest` ($0.30/$2.50) - Balanced performance
- **Simple Agents**: `gemini-flash-lite-latest` ($0.10/$0.40) - Simple tasks

**Image Generation:**
- The `image_generator` tool automatically uses `gemini-3-pro-image-preview` (Nano Banana Pro)
- Called by agents when images are needed (not configurable per agent)

See [backend/AGENT_MODEL_SELECTION.md](./backend/AGENT_MODEL_SELECTION.md) for detailed documentation.

### Database Setup

The application uses SQLAlchemy with PostgreSQL. Tables are automatically created on startup, but for production you should use migrations.

**Database Schema:**
- `users` - User accounts
- `organizations` - Organizations with metadata
- `organization_members` - User-organization relationships with permissions
- `threads` - Conversation threads with metadata (budget focus, response length, creativity)
- `messages` - Individual messages in threads
- `files` - Uploaded documents associated with organizations
- `chat_queries` - Legacy chat history (deprecated, use threads/messages)

**Running Migrations:**
```bash
cd backend
# Create initial migration (if needed)
alembic revision --autogenerate -m "Initial migration"
# Apply migrations
alembic upgrade head
```

### API Endpoints

**Users:**
- `POST /api/users` - Create a new user
- `GET /api/users` - List all users
- `GET /api/users/{user_id}` - Get user by ID

**Chat:**
- `POST /api/llm/chat` - Send chat message (non-streaming)
- `POST /api/llm/chat/stream` - Send chat message (SSE streaming)
- `GET /api/threads` - Get threads for user/organization
- `GET /api/threads/{thread_id}` - Get thread details
- `POST /api/threads` - Create new thread
- `PUT /api/threads/{thread_id}` - Update thread metadata
- `GET /api/threads/{thread_id}/messages` - Get messages for thread

**Files:**
- `POST /api/files/upload` - Upload file to organization
- `GET /api/organizations/{org_id}/files` - Get files for organization
- `GET /api/files/{file_id}/download` - Download file
- `DELETE /api/files/{file_id}` - Delete file

**Organizations:**
- `GET /api/organizations` - Get user's organizations
- `POST /api/organizations` - Create organization
- `GET /api/organizations/{org_id}` - Get organization details

**Other:**
- `GET /health` - Health check
- `GET /api` - API status
- `GET /docs` - Interactive API documentation (Swagger UI)

## 🧪 Testing

LabZ runs blocking backend and frontend quality, test, coverage, crew-validation,
ShellCheck, and build gates in GitHub Actions.

**Enforced Coverage:** 60% overall backend coverage and 70% frontend coverage across
the core module set declared in `frontend/vitest.config.ts`.

**Quick Commands:**

Backend (pytest):
```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest                # Run tests with enforced coverage
```

Frontend (Vitest):
```bash
cd frontend
npm test                        # Run tests
npm run test:coverage           # Run with coverage report
npm run test:ui                 # Run with UI for debugging
```

**CI/CD:** Quality gates run automatically on every push and pull request.

See [TESTING.md](./TESTING.md) for detailed testing guide including:
- Test structure and fixtures
- Writing new tests
- Debugging tests
- Best practices
- Troubleshooting

## 📝 License

ISC

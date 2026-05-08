# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MuscleGuard is an AI-powered fitness coaching application combining real-time heart rate monitoring (via HypeRate) with LangGraph ReAct agents. The backend is FastAPI + PostgreSQL + ChromaDB; the frontend is Next.js 14.

## Commands

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize exercise library (first run only)
python db/init_script.py

# Start backend (port 8000)
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev   # http://localhost:3000
```

### RAG Knowledge Base (optional, offline)

```bash
# Place PDF in data/document/, then:
python llm/rag/ingest_pdf.py
# ChromaDB is auto-populated on first backend startup
```

## Architecture

### Request Flow

```
HTTP Request
  → controller/  (route handlers)
  → services/    (business logic)
  → models/      (SQLModel ORM, PostgreSQL via asyncpg)
```

### Core Per-Set Workflow (`controller/sync.py`)

1. `POST /sync/resume_polling` — starts 2s HypeRate polling
2. `POST /sync/pause_polling` — stops polling, triggers:
   - `FatigueAnalyzer` computes score (0–100)
   - `SetsService.create_set()` persists the record
   - `LGFitnessAgent.lg_run_analysis()` runs LangGraph ReAct inference

### LangGraph Agent (`llm/langGraph/lg_agent.py`)

Dual-mode ReAct agent with two isolated memory threads:
- **Training mode** — `thread_id = str(plan_id)`, cross-set shared memory, uses `ANALYSIS_SYSTEM_PROMPT`
- **Chat mode** — `thread_id = "chat_{session_id}"`, uses `CHAT_SYSTEM_PROMPT`

Checkpoints are persisted to PostgreSQL via `AsyncPostgresSaver`. Memory summarization triggers when token count > 2000 (chat mode only), sliding the window and persisting summaries to `MemorySummary` table.

Agent tools (`llm/langGraph/lg_tools.py`):
- `calculate_1rm(weight, reps)` — Epley formula
- `get_exercise_history(exercise_id)` — historical sets
- `get_plan_history(limit)` — historical plans
- `get_sets_detail_by_plan_id(plan_id)` — plan details
- `search_exercise_knowledge(query)` — RAG dual-library retrieval

### RAG Knowledge Base (`llm/rag/`)

Two ChromaDB collections:
- `exercises` — ~860 exercises from `db/exercise.json`, MMR retrieval (k=10)
- `champion_book` — PDF fitness book converted to Markdown, MultiQueryRetriever + MMR (k=5)

### Fatigue Scoring (`services/fatigue_service.py`)

Score range 0–100 (higher = more fatigued):
- **Recovery score (0–70):** HRR% = (peak_hr − rest_hr) / peak_hr → thresholds at 18% and 12%
- **History score (0–30):** HR efficiency vs. historical average, linear interpolation

### Data Models (`models/`)

```
User (session_id PK)
  └── WorkoutPlan
        └── PlanExercise → BaseExercise (exercise library)
              └── ExerciseSet (weight, reps, peak_hr, rest_hr, score)
```

`session_id` doubles as the HypeRate device ID.

## Key Environment Variables (`.env`)

```
LLM_API_KEY=          # DeepSeek API key
LLM_MODEL_ID=         # e.g. deepseek-chat
LLM_BASE_URL=         # e.g. https://api.deepseek.com/v1
DATABASE_URL=         # postgresql+asyncpg://user:pass@host:5432/muscleguard
```

## Important Implementation Notes

- **Windows event loop:** `main.py` forces `WindowsSelectorEventLoopPolicy` — required for psycopg async on Windows. Do not remove.
- **Async throughout:** All DB operations use `AsyncSession` + asyncpg. Never use sync SQLAlchemy calls.
- **PostgreSQL JSONB:** `BaseExercise` stores arrays (`primary_muscles`, `secondary_muscles`, `instructions`, `images`) as JSONB. Queries use `jsonb_array_elements_text`.
- **LangGraph checkpoint tables** are auto-created by `AsyncPostgresSaver.setup()` on startup — no manual migration needed.
- **LLM is injected via config:** `config["configurable"]["llm"]` — the agent node reads the LLM from LangGraph config, not a module-level global.
- **Singleton services** (`HeartRateSyncService`, `LGFitnessAgent`) are stored on `app.state` and initialized in `lifespan.py`.

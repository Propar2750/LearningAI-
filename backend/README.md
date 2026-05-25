# Learning.AI backend

FastAPI service backed by Supabase Postgres. Serves the conversation graph to
the frontend in the shape defined by `frontend/src/types.ts`.

## Stack
- FastAPI + Uvicorn
- SQLAlchemy 2.0 (async, `asyncpg`) — app queries
- Alembic (sync, `psycopg`) — migrations (source of truth for schema)
- Supabase Postgres via the **session pooler** (port 5432)
- Managed with `uv`

## Configuration
The DB password is read from the **repo-root `.env`** (`DATABASE_PWD`). The
non-secret connection details (host/port/db/user) default to the Supabase
session pooler in `app/config.py` and can be overridden by env vars.

## ⚠️ ROS / PYTHONPATH note
This machine has ROS Humble on a global `PYTHONPATH`
(`/opt/ros/humble/...`), which leaks system packages into the venv and makes
`pytest` try to load ROS's pytest plugins (failing on `lark`). **Run backend
commands with a cleared `PYTHONPATH`:**

```bash
PYTHONPATH= .venv/bin/pytest
PYTHONPATH= .venv/bin/uvicorn app.main:app --port 8000
```

## Common commands (run from `backend/`)
```bash
# Migrations
.venv/bin/alembic upgrade head
.venv/bin/alembic revision --autogenerate -m "describe change"

# Seed a tiny dev graph (idempotent)
.venv/bin/python -m app.seed

# Run the API
PYTHONPATH= .venv/bin/uvicorn app.main:app --reload --port 8000

# Tests (against the live DB)
PYTHONPATH= .venv/bin/pytest -q
```

## Endpoints
- `GET /health` — liveness
- `GET /health/db` — runs `SELECT 1`
- `GET /api/graph` — full graph as `{ nodes, links }`
- `GET /api/nodes/{id}` — single node (404 if unknown)

## Schema (DAG)
- `graphs` (id, **user_id**, goal, created_at) — one immutable goal per graph
- `nodes` (id, graph_id, **heading**, kind, **input_prompt**, **ai_output**,
  **edge_value**, **description**, **summary**, created_at) — immutable
- `edges` (id, graph_id, source_id, target_id, edge_type) — multiple parents +
  typed edges (`subtopic`/`prerequisite`/`see-also`/`side-question`)

The API collapses this to the frontend contract: `heading` → `label`,
`input_prompt`/`ai_output` → `turn`, `edges` → `links`. `edge_value`,
`description`, `summary`, and `edge_type` are stored but not yet sent to the
frontend.

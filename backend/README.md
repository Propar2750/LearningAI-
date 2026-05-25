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

## Authentication
The `/api/*` endpoints require a **Supabase access token** sent as
`Authorization: Bearer <jwt>`. The frontend obtains it via Supabase OAuth
(GitHub / Google) and attaches it to every request. The backend verifies the
token locally against the project's JWKS endpoint (`app/auth.py`) and scopes all
queries to the token's `sub` (the Supabase user UUID), matched against
`graphs.user_id`. No token (or an invalid one) → `401`.

### One-time Supabase dashboard setup
Local verification uses **asymmetric signing keys**, and OAuth needs the
providers configured. Do this once in the Supabase dashboard:

1. **Migrate JWT signing keys** — Project Settings → JWT Keys → "Migrate JWT
   secret", then rotate so an ES256/RS256 key is *in use*. (Zero-downtime. Until
   this is done the JWKS endpoint is empty and token verification fails.)
2. **GitHub provider** — Auth → Providers → GitHub: create a GitHub OAuth App
   with callback `https://<project-ref>.supabase.co/auth/v1/callback`, paste
   Client ID/Secret.
3. **Google provider** — Auth → Providers → Google: create a Google Cloud OAuth
   (Web) client with the same Supabase callback as an authorized redirect URI,
   paste Client ID/Secret.
4. **Redirect allow list** — Auth → URL Configuration: add `http://localhost:5173`
   (and the prod origin later).
5. **Frontend env** — copy the project URL + publishable key into
   `frontend/.env.local` (see `frontend/.env.example`).

`SUPABASE_URL` defaults to the confirmed project in `app/config.py`; override via
env if the project moves.

## Endpoints
- `GET /health` — liveness (no auth)
- `GET /health/db` — runs `SELECT 1` (no auth)
- `GET /api/graph` — the signed-in user's graph as `{ nodes, links }` (auth required)
- `GET /api/nodes/{id}` — single node the user owns (404 if unknown or not theirs; auth required)

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

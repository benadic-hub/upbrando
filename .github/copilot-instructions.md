## Purpose

Quick, actionable guidance for AI coding agents working on this repository (FastAPI backend + async SQLAlchemy + Postgres).
Keep suggestions tightly scoped to discoverable patterns and files in this repo.

## Big-picture architecture
- Single FastAPI app under `app/` serving HTTP on port 8000 (see `app/main.py`).
- Async SQLAlchemy engine and session factory live in `app/database.py`.
- DB models are in `app/models.py` (SQLAlchemy 2.0-style mapped classes).
- Schemas (Pydantic v2) are in `app/schemas.py` and are used by endpoints.
- `app/crud.py` currently empty — this is the intended place for reusable DB access logic.
- Containerization: `Dockerfile` builds the app; `docker-compose.yml` wires the backend to a Postgres `db` service.

Why things are organized this way
- Async engine + asyncpg are used for asynchronous request handling with FastAPI.
- The `database.py` file centralizes engine/session creation; endpoints sometimes create ad-hoc sessionmakers (see `app/main.py`) — prefer reusing `AsyncSessionLocal` and `get_session()`.

Key files to inspect when making changes
- `app/main.py` — startup checks, health endpoint, and example CRUD-style endpoints (note: it creates a sessionmaker inline in endpoints).
- `app/database.py` — sets `DATABASE_URL` from environment and exports `engine`, `AsyncSessionLocal`, `Base`, and `get_session()`.
- `app/models.py` — SQLAlchemy mapped classes (example: `Agent` table and columns).
- `app/schemas.py` — Pydantic v2 models (note `model_config = {"from_attributes": True}` in output models).
- `app/crud.py` — place to add ORM helpers and encapsulate DB queries (currently empty).
- `Dockerfile` and `docker-compose.yml` — how the app is run in development; `docker-compose.yml` sets the `DATABASE_URL` env used by `database.py`.

Run / build / debug workflows (discoverable from files)
- Docker (recommended for parity with repo):
  - `docker-compose up --build` (compose file maps port `8000:8000` and starts a Postgres container named `db`).
- Local (developer):
  - Ensure `DATABASE_URL` env var is set (or create `backend/.env`). Example:

    DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cossmicrings

  - Install deps from `requirements.txt` and run:

    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

- DB bootstrap: there is no migrations system in the repo. To create tables from models, run a tiny script (run from the project root):

```python
from app.database import engine, Base
import asyncio

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(create_tables())
```

Project-specific conventions and patterns
- Database URL requirement: `app/database.py` raises if `DATABASE_URL` is empty and instructs placing it in `backend/.env`. Follow that convention when running locally.
- Async SQLAlchemy usage: code expects `create_async_engine`, `async_sessionmaker`, and `AsyncSession`.
- Pydantic v2: output models set `model_config = {"from_attributes": True}`; when converting DB objects prefer returning mappings or using `from_attributes`.
- Minimal endpoints in `app/main.py` sometimes use raw SQL (e.g. `SELECT * FROM agents`) and ad-hoc sessionmakers. Prefer:
  - Using `AsyncSessionLocal` from `app/database.py` or the `get_session()` dependency.
  - Using ORM queries or SQLAlchemy Core instead of `SELECT *` to preserve column typing and avoid injection risk.

Integration points and external dependencies
- Postgres is the only external service wired in `docker-compose.yml`.
- Primary Python deps: FastAPI, Uvicorn, SQLAlchemy, asyncpg, python-dotenv. Note `psycopg2-binary` is listed in `requirements.txt` but is not used by asyncpg; avoid mixing sync adapters into async code.

Editing guidance for AI agents (do this, not that)
- Do:
  - Reuse `AsyncSessionLocal` and `get_session()` from `app/database.py` when adding DB logic.
  - Add reusable DB operations to `app/crud.py` (keep business logic out of route handlers).
  - Preserve async APIs (don't introduce blocking DB calls). If you must use sync code, isolate it behind `run_in_executor` or convert to async-compatible libs.
  - Keep endpoint shapes similar to existing ones: POST `/agents` accepts `AgentCreate`, GET `/agents` returns a list of agents as mappings.

- Don't:
  - Replace the async engine with a sync engine without a clear migration plan.
  - Assume a migration tool exists — none is present. If you add Alembic or similar, include a short README and necessary env instructions.

Examples drawn from the codebase
- Creating a new agent (existing pattern): `app/main.py` does `new_agent = Agent(**agent.dict()); session.add(new_agent); await session.commit()`.
- Reading agents (current): `result = await session.execute(text("SELECT * FROM agents")); agents = result.fetchall(); return {"agents": [dict(row._mapping) for row in agents]}` — prefer using ORM queries and returning Pydantic models.

Low-risk improvements you can propose or implement
- Move inline sessionmaker usage in `app/main.py` to use `AsyncSessionLocal` or the `get_session()` dependency.
- Implement basic CRUD functions in `app/crud.py` for agents and swap raw SQL for ORM usage.
- Add a short `scripts/create_tables.py` (or management command) that runs the `Base.metadata.create_all` snippet above.

If anything in this file is unclear or you want concrete edits (e.g., convert endpoints to DI style, add migrations, or create the CRUD layer), say which task and I'll implement it.

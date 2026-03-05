from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import asyncpg


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings  # noqa: E402


MIGRATION_LOCK_ID = 847221905135


def _to_asyncpg_dsn(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    if database_url.startswith("postgresql://"):
        return database_url
    raise RuntimeError("DATABASE_URL must be a PostgreSQL URL")


async def _run_upgrade() -> None:
    dsn = _to_asyncpg_dsn(settings.DATABASE_URL)
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute("SELECT pg_advisory_lock($1)", MIGRATION_LOCK_ID)
        print("Migration lock acquired")
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            "head",
            cwd=str(ROOT_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=os.environ.copy(),
        )
        assert proc.stdout is not None
        async for chunk in proc.stdout:
            print(chunk.decode("utf-8").rstrip())
        code = await proc.wait()
        if code != 0:
            raise RuntimeError(f"alembic upgrade head failed with exit code {code}")
        print("Migrations applied successfully")
    finally:
        try:
            await conn.execute("SELECT pg_advisory_unlock($1)", MIGRATION_LOCK_ID)
        finally:
            await conn.close()


def main() -> int:
    asyncio.run(_run_upgrade())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

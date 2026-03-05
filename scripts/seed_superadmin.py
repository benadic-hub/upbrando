from __future__ import annotations

import asyncio
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal
from app.services.bootstrap import get_bootstrap_status, seed_superadmin_from_settings


async def seed() -> None:
    async with SessionLocal() as session:
        created, user = await seed_superadmin_from_settings(session)
        status = await get_bootstrap_status(session)
        if created:
            print(f"Created SUPERADMIN user: {user.email}")
        else:
            print(f"SUPERADMIN already exists: {user.email}")
        print(
            "Bootstrap status -> "
            f"tenant_exists={status.tenant_exists}, "
            f"root_department_exists={status.root_department_exists}, "
            f"superadmin_exists={status.superadmin_exists}, "
            f"total_users={status.total_users}"
        )


if __name__ == "__main__":
    asyncio.run(seed())

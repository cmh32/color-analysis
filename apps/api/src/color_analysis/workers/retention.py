import asyncio

from color_analysis.db.base import SessionLocal
from color_analysis.core.session_service import SessionService


async def _sweep() -> int:
    async with SessionLocal() as db:
        service = SessionService(db)
        return await service.sweep_expired_sessions()


def run_retention_sweep() -> int:
    return asyncio.run(_sweep())


if __name__ == "__main__":
    deleted = run_retention_sweep()
    print(f"Deleted {deleted} expired sessions")

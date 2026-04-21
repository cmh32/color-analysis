import asyncio

from color_analysis.db.base import SessionLocal
from color_analysis.core.session_service import SessionService
from color_analysis.storage.r2 import R2Client
from color_analysis.storage.redis import RedisQueue

_r2 = R2Client()
_redis = RedisQueue()


async def _sweep() -> int:
    async with SessionLocal() as db:
        service = SessionService(db, _r2, _redis)
        return await service.sweep_expired_sessions()


def run_retention_sweep() -> int:
    return asyncio.run(_sweep())


if __name__ == "__main__":
    deleted = run_retention_sweep()
    print(f"Deleted {deleted} expired sessions")

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from color_analysis.api.deps import db_session_dep, require_admin_token
from color_analysis.db.models.audit_trace import AuditTrace

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/sessions/{session_id}/trace", dependencies=[Depends(require_admin_token)])
async def get_trace(session_id: str, db: AsyncSession = Depends(db_session_dep)) -> dict[str, object]:
    parsed = uuid.UUID(session_id)
    rows = await db.scalars(select(AuditTrace).where(AuditTrace.session_id == parsed))
    traces = [
        {
            "stage": row.stage,
            "payload": row.payload,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
    return {"session_id": session_id, "trace": traces}

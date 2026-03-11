from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal, Role, require_roles
from app.db.base import get_db_session
from app.db.models import AuditEvent

router = APIRouter(prefix='/audit', tags=['audit'])


class AuditEventOut(BaseModel):
    id: UUID
    actor_sub: str
    action: str
    entity_type: str
    entity_id: str
    occurred_at: datetime
    previous_hash: str | None
    event_hash: str


@router.get('/events', response_model=list[AuditEventOut])
async def recent_events(
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
) -> list[AuditEventOut]:
    stmt = select(AuditEvent)
    if Role.SUPER_ADMIN not in principal.roles:
        if principal.organization_id is None:
            return []
        try:
            org_id = UUID(principal.organization_id)
        except ValueError:
            return []
        stmt = stmt.where(AuditEvent.organization_id == org_id)
    stmt = stmt.order_by(desc(AuditEvent.occurred_at)).limit(200)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        AuditEventOut(
            id=row.id,
            actor_sub=row.actor_sub,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            occurred_at=row.occurred_at,
            previous_hash=row.previous_hash,
            event_hash=row.event_hash,
        )
        for row in rows
    ]

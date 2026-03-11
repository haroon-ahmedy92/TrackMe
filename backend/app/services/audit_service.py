from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent


class AuditService:
    async def append_event(
        self,
        session: AsyncSession,
        actor_sub: str,
        organization_id: str | None,
        action: str,
        entity_type: str,
        entity_id: str,
        metadata: dict,
    ) -> AuditEvent:
        org_uuid = uuid.UUID(organization_id) if organization_id else None
        latest_stmt = select(AuditEvent)
        if org_uuid is None:
            latest_stmt = latest_stmt.where(AuditEvent.organization_id.is_(None))
        else:
            latest_stmt = latest_stmt.where(AuditEvent.organization_id == org_uuid)
        latest_stmt = latest_stmt.order_by(desc(AuditEvent.occurred_at)).limit(1)
        latest = (await session.execute(latest_stmt)).scalar_one_or_none()
        previous_hash = latest.event_hash if latest else None

        occurred_at = datetime.now(timezone.utc)
        metadata_json = json.dumps(metadata, sort_keys=True, separators=(',', ':'))
        raw = '|'.join([
            previous_hash or '',
            actor_sub,
            action,
            entity_type,
            entity_id,
            occurred_at.isoformat(),
            metadata_json,
        ])
        event_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()

        event = AuditEvent(
            actor_sub=actor_sub,
            organization_id=org_uuid,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata,
            occurred_at=occurred_at,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        session.add(event)
        await session.flush()
        return event

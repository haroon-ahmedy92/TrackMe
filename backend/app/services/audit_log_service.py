from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


class AuditLogService:
    async def append(
        self,
        session: AsyncSession,
        *,
        org_id: str | None,
        actor_sub: str,
        action: str,
        entity_type: str,
        entity_id: str,
        metadata: dict,
    ) -> AuditLog:
        org_uuid = uuid.UUID(org_id) if org_id else None
        latest_stmt = select(AuditLog)
        if org_uuid is None:
            latest_stmt = latest_stmt.where(AuditLog.org_id.is_(None))
        else:
            latest_stmt = latest_stmt.where(AuditLog.org_id == org_uuid)
        latest_stmt = latest_stmt.order_by(desc(AuditLog.occurred_at)).limit(1)
        latest = (await session.execute(latest_stmt)).scalar_one_or_none()
        previous_hash = latest.event_hash if latest else None
        occurred_at = datetime.now(timezone.utc)
        metadata_json = json.dumps(metadata, sort_keys=True, separators=(',', ':'))
        chain_raw = '|'.join(
            [
                previous_hash or '',
                org_id or '',
                actor_sub,
                action,
                entity_type,
                entity_id,
                occurred_at.isoformat(),
                metadata_json,
            ]
        )
        event_hash = hashlib.sha256(chain_raw.encode('utf-8')).hexdigest()

        record = AuditLog(
            org_id=org_uuid,
            actor_sub=actor_sub,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata,
            occurred_at=occurred_at,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        session.add(record)
        await session.flush()
        return record

    async def verify_chain(self, session: AsyncSession, *, org_id: str) -> tuple[bool, int, str | None, str | None]:
        org_uuid = uuid.UUID(org_id)
        stmt = (
            select(AuditLog)
            .where(AuditLog.org_id == org_uuid)
            .order_by(AuditLog.occurred_at.asc())
        )
        rows = list((await session.execute(stmt)).scalars().all())
        previous_hash: str | None = None
        for row in rows:
            if row.previous_hash != previous_hash:
                return False, len(rows), str(row.id), 'previous_hash_mismatch'

            metadata_json = json.dumps(row.metadata_json, sort_keys=True, separators=(',', ':'))
            chain_raw = '|'.join(
                [
                    previous_hash or '',
                    str(row.org_id) if row.org_id else '',
                    row.actor_sub,
                    row.action,
                    row.entity_type,
                    row.entity_id,
                    row.occurred_at.isoformat(),
                    metadata_json,
                ]
            )
            expected = hashlib.sha256(chain_raw.encode('utf-8')).hexdigest()
            if row.event_hash != expected:
                return False, len(rows), str(row.id), 'event_hash_mismatch'
            previous_hash = row.event_hash

        return True, len(rows), None, None

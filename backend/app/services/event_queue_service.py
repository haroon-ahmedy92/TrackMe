from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import EventQueueItem, QueuedEventStatus
from app.schemas.events import PlatformEventEnvelope


@dataclass(frozen=True)
class QueuePublishResult:
    record: EventQueueItem
    created: bool


class EventQueue(Protocol):
    async def publish(self, session: AsyncSession, envelope: PlatformEventEnvelope) -> QueuePublishResult:
        ...

    async def claim_next(
        self,
        session: AsyncSession,
        *,
        worker_name: str,
        topics: set[str] | None = None,
    ) -> EventQueueItem | None:
        ...

    async def mark_completed(self, session: AsyncSession, *, record: EventQueueItem) -> None:
        ...

    async def mark_failed(
        self,
        session: AsyncSession,
        *,
        record: EventQueueItem,
        error_message: str,
        retry_delay_seconds: int | None = None,
    ) -> None:
        ...


class SqlAlchemyEventQueueService:
    async def publish(self, session: AsyncSession, envelope: PlatformEventEnvelope) -> QueuePublishResult:
        existing = (
            await session.execute(
                select(EventQueueItem).where(EventQueueItem.idempotency_key == envelope.idempotency_key)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return QueuePublishResult(record=existing, created=False)

        record = EventQueueItem(
            org_id=envelope.org_id,
            topic=envelope.topic.value,
            entity_type=envelope.entity_type,
            entity_id=envelope.entity_id,
            producer=envelope.producer,
            idempotency_key=envelope.idempotency_key,
            payload_json=envelope.payload,
            headers_json=envelope.headers,
            status=QueuedEventStatus.PENDING,
            available_at=envelope.available_at or datetime.now(timezone.utc),
            locked_at=None,
            locked_by=None,
            handled_at=None,
            failed_at=None,
            attempt_count=0,
            last_error=None,
            created_at=datetime.now(timezone.utc),
        )
        session.add(record)
        await session.flush()
        return QueuePublishResult(record=record, created=True)

    async def claim_next(
        self,
        session: AsyncSession,
        *,
        worker_name: str,
        topics: set[str] | None = None,
    ) -> EventQueueItem | None:
        now = datetime.now(timezone.utc)
        reclaim_before = now - timedelta(seconds=settings.event_queue_claim_timeout_seconds)
        stmt = (
            select(EventQueueItem)
            .where(
                or_(
                    EventQueueItem.status == QueuedEventStatus.PENDING,
                    and_(
                        EventQueueItem.status == QueuedEventStatus.PROCESSING,
                        EventQueueItem.locked_at.is_not(None),
                        EventQueueItem.locked_at < reclaim_before,
                    ),
                ),
                EventQueueItem.available_at <= now,
            )
            .order_by(EventQueueItem.available_at.asc(), EventQueueItem.created_at.asc())
            .limit(1)
        )
        if topics:
            stmt = stmt.where(EventQueueItem.topic.in_(sorted(topics)))

        record = (await session.execute(stmt)).scalar_one_or_none()
        if record is None:
            return None

        record.status = QueuedEventStatus.PROCESSING
        record.locked_at = now
        record.locked_by = worker_name
        record.attempt_count += 1
        await session.flush()
        return record

    async def mark_completed(self, session: AsyncSession, *, record: EventQueueItem) -> None:
        record.status = QueuedEventStatus.COMPLETED
        record.handled_at = datetime.now(timezone.utc)
        record.locked_at = None
        record.locked_by = None
        record.last_error = None
        await session.flush()

    async def mark_failed(
        self,
        session: AsyncSession,
        *,
        record: EventQueueItem,
        error_message: str,
        retry_delay_seconds: int | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        record.last_error = error_message[:280]
        record.locked_at = None
        record.locked_by = None
        if record.attempt_count >= settings.event_queue_max_attempts:
            record.status = QueuedEventStatus.FAILED
            record.failed_at = now
        else:
            record.status = QueuedEventStatus.PENDING
            record.available_at = now + timedelta(seconds=retry_delay_seconds or settings.event_queue_retry_delay_seconds)
        await session.flush()

    def to_envelope(self, record: EventQueueItem) -> PlatformEventEnvelope:
        return PlatformEventEnvelope(
            topic=record.topic,
            org_id=record.org_id,
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            producer=record.producer,
            occurred_at=record.created_at,
            idempotency_key=record.idempotency_key,
            payload=record.payload_json,
            headers=record.headers_json,
            available_at=record.available_at,
        )


@dataclass
class _MemoryRecord:
    id: str
    topic: str
    idempotency_key: str
    payload_json: dict
    headers_json: dict
    entity_type: str
    entity_id: str
    producer: str
    org_id: str | None
    created_at: datetime
    available_at: datetime
    status: str
    attempt_count: int = 0
    locked_at: datetime | None = None
    locked_by: str | None = None
    handled_at: datetime | None = None
    failed_at: datetime | None = None
    last_error: str | None = None


class InMemoryEventQueueService:
    def __init__(self) -> None:
        self._records: list[_MemoryRecord] = []

    async def publish(self, session, envelope: PlatformEventEnvelope) -> QueuePublishResult:  # pragma: no cover - thin adapter
        for record in self._records:
            if record.idempotency_key == envelope.idempotency_key:
                return QueuePublishResult(record=record, created=False)  # type: ignore[arg-type]
        record = _MemoryRecord(
            id=str(uuid4()),
            topic=envelope.topic.value,
            idempotency_key=envelope.idempotency_key,
            payload_json=envelope.payload,
            headers_json=envelope.headers,
            entity_type=envelope.entity_type,
            entity_id=envelope.entity_id,
            producer=envelope.producer,
            org_id=str(envelope.org_id) if envelope.org_id else None,
            created_at=datetime.now(timezone.utc),
            available_at=envelope.available_at or datetime.now(timezone.utc),
            status=QueuedEventStatus.PENDING.value,
        )
        self._records.append(record)
        return QueuePublishResult(record=record, created=True)  # type: ignore[arg-type]

    async def claim_next(self, session, *, worker_name: str, topics: set[str] | None = None):  # pragma: no cover - thin adapter
        now = datetime.now(timezone.utc)
        for record in sorted(self._records, key=lambda item: (item.available_at, item.created_at)):
            if topics and record.topic not in topics:
                continue
            if record.available_at > now:
                continue
            if record.status not in {QueuedEventStatus.PENDING.value, QueuedEventStatus.PROCESSING.value}:
                continue
            if record.status == QueuedEventStatus.PROCESSING.value and record.locked_at:
                if record.locked_at >= now - timedelta(seconds=settings.event_queue_claim_timeout_seconds):
                    continue
            record.status = QueuedEventStatus.PROCESSING.value
            record.locked_at = now
            record.locked_by = worker_name
            record.attempt_count += 1
            return record
        return None

    async def mark_completed(self, session, *, record):  # pragma: no cover - thin adapter
        record.status = QueuedEventStatus.COMPLETED.value
        record.handled_at = datetime.now(timezone.utc)
        record.locked_at = None
        record.locked_by = None
        record.last_error = None

    async def mark_failed(self, session, *, record, error_message: str, retry_delay_seconds: int | None = None):  # pragma: no cover - thin adapter
        now = datetime.now(timezone.utc)
        record.last_error = error_message
        record.locked_at = None
        record.locked_by = None
        if record.attempt_count >= settings.event_queue_max_attempts:
            record.status = QueuedEventStatus.FAILED.value
            record.failed_at = now
        else:
            record.status = QueuedEventStatus.PENDING.value
            record.available_at = now + timedelta(seconds=retry_delay_seconds or settings.event_queue_retry_delay_seconds)

    def to_envelope(self, record) -> PlatformEventEnvelope:  # pragma: no cover - thin adapter
        return PlatformEventEnvelope(
            topic=record.topic,
            org_id=record.org_id,
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            producer=record.producer,
            occurred_at=record.created_at,
            idempotency_key=record.idempotency_key,
            payload=record.payload_json,
            headers=record.headers_json,
            available_at=record.available_at,
        )

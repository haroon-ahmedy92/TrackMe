from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CheckInMode, Device, TelemetryEvent
from app.schemas.telemetry import TelemetryCheckInRequest
from app.services.location_confidence import LocationConfidenceService


class TelemetryService:
    def __init__(self, confidence_service: LocationConfidenceService) -> None:
        self.confidence_service = confidence_service

    async def record_checkin(
        self,
        session: AsyncSession,
        payload: TelemetryCheckInRequest,
        principal_org_id: str | None,
    ) -> TelemetryEvent:
        device_stmt = select(Device).where(Device.id == payload.device_id)
        device = (await session.execute(device_stmt)).scalar_one_or_none()
        if device is None:
            raise ValueError('Unknown device_id')
        if principal_org_id is not None and str(device.organization_id) != principal_org_id:
            raise PermissionError('Tenant access denied')

        selected = self.confidence_service.choose_best_signal(payload.signals)

        telemetry_event = TelemetryEvent(
            device_id=payload.device_id,
            mode=CheckInMode(payload.mode.value),
            checkin_at=payload.checkin_at,
            battery_percent=payload.battery_percent,
            telemetry_signature=payload.telemetry_signature,
            telemetry_algorithm=payload.telemetry_algorithm,
            telemetry_key_id=payload.telemetry_key_id,
            integrity_token=payload.integrity_token,
            is_approximate=selected.signal.is_approximate if selected else False,
            confidence_score=selected.confidence_score if selected else None,
            method_label=selected.signal.method_label if selected else None,
            latitude=selected.signal.latitude if selected else None,
            longitude=selected.signal.longitude if selected else None,
            accuracy_meters=selected.signal.accuracy_meters if selected else None,
            location_geom=(
                func.ST_SetSRID(func.ST_MakePoint(selected.signal.longitude, selected.signal.latitude), 4326)
                if selected
                else None
            ),
        )

        session.add(telemetry_event)
        await session.flush()
        return telemetry_event

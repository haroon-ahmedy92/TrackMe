from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CheckInMode, Device, LocationEvent
from app.schemas.platform import LocationIngestRequest
from app.services.integrity_verification_service import IntegrityVerificationService
from app.services.ip_enrichment_service import IpEnrichmentService
from app.services.rules_engine_service import RulesEngineService
from app.services.geofence_service import GeofenceService
from app.services.signed_telemetry_service import SignedTelemetryService


@dataclass(frozen=True)
class IngestionResult:
    event: LocationEvent
    duplicate: bool
    rule_matches: list[str]
    suspicious_alerts: list[str]
    telemetry_digest_matches: bool
    integrity_status: str
    geofence_events: list


class LocationIngestionService:
    def __init__(
        self,
        signed_telemetry_service: SignedTelemetryService,
        integrity_verification_service: IntegrityVerificationService,
        ip_enrichment_service: IpEnrichmentService,
        rules_engine_service: RulesEngineService,
        geofence_service: GeofenceService,
    ) -> None:
        self.signed_telemetry_service = signed_telemetry_service
        self.integrity_verification_service = integrity_verification_service
        self.ip_enrichment_service = ip_enrichment_service
        self.rules_engine_service = rules_engine_service
        self.geofence_service = geofence_service

    async def ingest(self, session: AsyncSession, payload: LocationIngestRequest) -> IngestionResult:
        device = (await session.execute(select(Device).where(Device.id == payload.device_id))).scalar_one_or_none()
        if device is None:
            raise ValueError('Unknown device_id')
        if device.organization_id != payload.org_id:
            raise ValueError('Device does not belong to tenant org.')

        existing_stmt = select(LocationEvent).where(
            LocationEvent.device_id == payload.device_id,
            LocationEvent.idempotency_key == payload.idempotency_key,
        )
        existing = (await session.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            return IngestionResult(
                event=existing,
                duplicate=True,
                rule_matches=[],
                suspicious_alerts=[],
                telemetry_digest_matches=bool(payload.telemetry_payload_hash),
                integrity_status='duplicate',
                geofence_events=[],
            )

        telemetry_digest_matches = self._payload_digest(payload) == (payload.telemetry_payload_hash or '')
        verification = await self.signed_telemetry_service.verify_placeholder(
            session=session,
            device_id=payload.device_id,
            telemetry_signature=payload.telemetry_signature,
            telemetry_key_id=payload.telemetry_key_id,
            telemetry_payload_hash=payload.telemetry_payload_hash,
        )
        telemetry_verified = verification.verified and telemetry_digest_matches
        integrity = self.integrity_verification_service.assess(payload.integrity_verdict)
        ip = await self.ip_enrichment_service.approximate(payload.ip_address)
        rules = await self.rules_engine_service.evaluate_location(session=session, payload=payload)
        alerts = self._build_alerts(
            payload=payload,
            verification_reason=verification.reason,
            telemetry_verified=telemetry_verified,
            telemetry_digest_matches=telemetry_digest_matches,
            integrity_trusted=integrity.trusted,
            ip_is_approximate=ip.is_approximate,
        )

        event = LocationEvent(
            org_id=payload.org_id,
            device_id=payload.device_id,
            idempotency_key=payload.idempotency_key,
            mode=CheckInMode(payload.mode.value),
            captured_at=payload.captured_at,
            received_at=datetime.now(timezone.utc),
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_meters=payload.accuracy_meters,
            precision=payload.precision,
            confidence_score=payload.confidence_score,
            source_methods={'methods': payload.source_methods, 'alerts': alerts},
            network_type=payload.network_type,
            battery_percent=payload.battery_percent,
            motion_state=payload.motion_state,
            ip_address=ip.ip_address,
            ip_country=ip.country,
            ip_city=ip.city,
            ip_latitude=ip.latitude,
            ip_longitude=ip.longitude,
            ip_accuracy_km=ip.accuracy_km,
            is_ip_approximate=ip.is_approximate,
            telemetry_signature=payload.telemetry_signature,
            telemetry_key_id=payload.telemetry_key_id,
            telemetry_verified=telemetry_verified,
            integrity_verdict=(payload.integrity_verdict or integrity.status)[:64],
            location_geom=(
                func.ST_SetSRID(func.ST_MakePoint(payload.longitude, payload.latitude), 4326)
                if payload.longitude is not None and payload.latitude is not None
                else None
            ),
        )
        session.add(event)
        await session.flush()
        geofence_events = await self.geofence_service.process_location_event(session, location_event=event)
        geofence_matches = [f'GEOFENCE_{geofence_event.event_type.value.upper()}:{geofence_event.geofence_id}' for geofence_event in geofence_events]
        return IngestionResult(
            event=event,
            duplicate=False,
            rule_matches=sorted(set([*rules.matches, *geofence_matches])),
            suspicious_alerts=alerts,
            telemetry_digest_matches=telemetry_digest_matches,
            integrity_status=integrity.status,
            geofence_events=geofence_events,
        )

    def _payload_digest(self, payload: LocationIngestRequest) -> str:
        digest_fields = {
            'org_id': str(payload.org_id),
            'device_id': str(payload.device_id),
            'mode': payload.mode.value,
            'idempotency_key': payload.idempotency_key,
            'captured_at': payload.captured_at.isoformat(),
            'latitude': payload.latitude,
            'longitude': payload.longitude,
            'accuracy_meters': payload.accuracy_meters,
            'precision': payload.precision.value,
            'confidence_score': payload.confidence_score,
            'source_methods': payload.source_methods,
            'network_type': payload.network_type,
            'battery_percent': payload.battery_percent,
            'motion_state': payload.motion_state,
            'integrity_verdict': payload.integrity_verdict,
            'ip_address': payload.ip_address,
        }
        canonical = json.dumps(digest_fields, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    def _build_alerts(
        self,
        *,
        payload: LocationIngestRequest,
        verification_reason: str,
        telemetry_verified: bool,
        telemetry_digest_matches: bool,
        integrity_trusted: bool,
        ip_is_approximate: bool,
    ) -> list[str]:
        alerts: list[str] = []
        if not telemetry_verified:
            alerts.append(f'UNVERIFIED_TELEMETRY:{verification_reason}')
        if not telemetry_digest_matches:
            alerts.append('TELEMETRY_DIGEST_MISMATCH')
        if not integrity_trusted:
            alerts.append('INTEGRITY_NOT_TRUSTED')
        if payload.confidence_score is not None and payload.confidence_score < 30:
            alerts.append('LOW_CONFIDENCE_SIGNAL')
        if ip_is_approximate and payload.precision.value == 'approximate':
            alerts.append('APPROXIMATE_LOCATION_ONLY')
        if any('mock' in method.lower() for method in payload.source_methods):
            alerts.append('POTENTIAL_MOCK_LOCATION_SIGNAL')
        captured_at = payload.captured_at
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=timezone.utc)
        age_seconds = int((datetime.now(timezone.utc) - captured_at).total_seconds())
        if age_seconds > 6 * 60 * 60:
            alerts.append('STALE_CAPTURE_TIMESTAMP')
        return sorted(set(alerts))

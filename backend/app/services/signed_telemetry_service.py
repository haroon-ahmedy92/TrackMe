from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DeviceKey


@dataclass(frozen=True)
class TelemetryVerification:
    verified: bool
    digest_matches: bool
    reason: str


class SignedTelemetryService:
    async def verify_placeholder(
        self,
        session: AsyncSession,
        *,
        device_id,
        telemetry_signature: str | None,
        telemetry_key_id: str | None,
        telemetry_payload_hash: str | None,
    ) -> TelemetryVerification:
        if telemetry_signature is None or telemetry_key_id is None or telemetry_payload_hash is None:
            return TelemetryVerification(
                verified=False,
                digest_matches=False,
                reason='missing_signature_or_key_id_or_payload_hash',
            )

        if not _is_hex_digest(telemetry_payload_hash):
            return TelemetryVerification(verified=False, digest_matches=False, reason='invalid_payload_hash_format')

        stmt = select(DeviceKey).where(
            DeviceKey.device_id == device_id,
            DeviceKey.key_id == telemetry_key_id,
            DeviceKey.is_active.is_(True),
        )
        key = (await session.execute(stmt)).scalar_one_or_none()
        if key is None:
            return TelemetryVerification(verified=False, digest_matches=False, reason='unknown_device_key')

        expected_signature = hashlib.sha256(
            f'{telemetry_key_id}:{telemetry_payload_hash}'.encode('utf-8')
        ).hexdigest()
        if telemetry_signature != expected_signature:
            return TelemetryVerification(verified=False, digest_matches=True, reason='signature_mismatch')

        return TelemetryVerification(verified=True, digest_matches=True, reason='placeholder_verified')


def _is_hex_digest(value: str) -> bool:
    return bool(re.fullmatch(r'[a-fA-F0-9]{64,128}', value))

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import DeviceKey


@dataclass(frozen=True)
class TelemetryVerification:
    accepted: bool
    verified: bool
    digest_matches: bool
    reason: str


class SignedTelemetryService:
    OPTIONAL_MODE = 'optional'
    REQUIRED_MODE = 'required'
    PLACEHOLDER_ALGORITHM = 'SHA256_KEYID_PAYLOAD_HASH_PLACEHOLDER'
    ECDSA_SHA256_ALGORITHMS = {'SHA256withECDSA', 'ANDROID_KEYSTORE_ECDSA_SHA256'}
    RSA_SHA256_ALGORITHMS = {'SHA256withRSA', 'ANDROID_KEYSTORE_RSA_SHA256'}

    async def verify_location_request(self, session: AsyncSession, *, device_id: UUID, payload) -> TelemetryVerification:
        expected_hash = self.compute_location_payload_hash(payload)
        return await self.verify_signed_payload(
            session,
            device_id=device_id,
            telemetry_signature=payload.telemetry_signature,
            telemetry_key_id=payload.telemetry_key_id,
            telemetry_payload_hash=payload.telemetry_payload_hash,
            telemetry_algorithm=getattr(payload, 'telemetry_algorithm', None),
            expected_payload_hash=expected_hash,
        )

    async def verify_checkin_request(self, session: AsyncSession, *, device_id: UUID, payload) -> TelemetryVerification:
        expected_hash = self.compute_checkin_payload_hash(payload)
        return await self.verify_signed_payload(
            session,
            device_id=device_id,
            telemetry_signature=payload.telemetry_signature,
            telemetry_key_id=payload.telemetry_key_id,
            telemetry_payload_hash=payload.telemetry_payload_hash,
            telemetry_algorithm=getattr(payload, 'telemetry_algorithm', None),
            expected_payload_hash=expected_hash,
        )

    async def verify_command_ack_request(
        self,
        session: AsyncSession,
        *,
        command_id: UUID,
        device_id: UUID,
        payload,
    ) -> TelemetryVerification:
        expected_hash = self.compute_command_ack_payload_hash(command_id=command_id, payload=payload)
        return await self.verify_signed_payload(
            session,
            device_id=device_id,
            telemetry_signature=payload.telemetry_signature,
            telemetry_key_id=payload.key_id,
            telemetry_payload_hash=payload.telemetry_payload_hash,
            telemetry_algorithm=getattr(payload, 'telemetry_algorithm', None),
            expected_payload_hash=expected_hash,
        )

    async def verify_signed_payload(
        self,
        session: AsyncSession,
        *,
        device_id: UUID,
        telemetry_signature: str | None,
        telemetry_key_id: str | None,
        telemetry_payload_hash: str | None,
        telemetry_algorithm: str | None,
        expected_payload_hash: str,
    ) -> TelemetryVerification:
        if self._missing_signature_fields(
            telemetry_signature=telemetry_signature,
            telemetry_key_id=telemetry_key_id,
            telemetry_payload_hash=telemetry_payload_hash,
            telemetry_algorithm=telemetry_algorithm,
        ):
            if settings.signed_telemetry_mode == self.REQUIRED_MODE:
                return TelemetryVerification(
                    accepted=False,
                    verified=False,
                    digest_matches=False,
                    reason='signature_required',
                )
            return TelemetryVerification(
                accepted=True,
                verified=False,
                digest_matches=False,
                reason='unsigned_optional_mode',
            )

        assert telemetry_signature is not None
        assert telemetry_key_id is not None
        assert telemetry_payload_hash is not None
        assert telemetry_algorithm is not None

        if not _is_hex_digest(telemetry_payload_hash):
            return TelemetryVerification(False, False, False, 'invalid_payload_hash_format')

        digest_matches = hmac.compare_digest(telemetry_payload_hash, expected_payload_hash)
        if not digest_matches:
            return TelemetryVerification(False, False, False, 'payload_hash_mismatch')

        stmt = select(DeviceKey).where(DeviceKey.device_id == device_id, DeviceKey.key_id == telemetry_key_id)
        key = (await session.execute(stmt)).scalar_one_or_none()
        if key is None:
            return TelemetryVerification(False, False, True, 'unknown_device_key')
        if key.revoked_at is not None:
            return TelemetryVerification(False, False, True, 'revoked_device_key')
        if not key.is_active:
            return TelemetryVerification(False, False, True, 'inactive_device_key')

        if telemetry_algorithm == self.PLACEHOLDER_ALGORITHM:
            if not settings.allow_placeholder_signed_telemetry:
                return TelemetryVerification(False, False, True, 'placeholder_signatures_disabled')
            verified = self._verify_placeholder_signature(
                telemetry_signature=telemetry_signature,
                telemetry_key_id=telemetry_key_id,
                telemetry_payload_hash=telemetry_payload_hash,
            )
        else:
            verified = self._verify_asymmetric_signature(
                public_key_pem=key.public_key_pem,
                telemetry_algorithm=telemetry_algorithm,
                telemetry_signature=telemetry_signature,
                telemetry_payload_hash=telemetry_payload_hash,
            )

        if not verified:
            return TelemetryVerification(False, False, True, 'signature_mismatch')

        key.last_used_at = datetime.now(timezone.utc)
        return TelemetryVerification(True, True, True, 'verified')

    async def verify_placeholder(
        self,
        session: AsyncSession,
        *,
        device_id,
        telemetry_signature: str | None,
        telemetry_key_id: str | None,
        telemetry_payload_hash: str | None,
    ) -> TelemetryVerification:
        return await self.verify_signed_payload(
            session,
            device_id=device_id,
            telemetry_signature=telemetry_signature,
            telemetry_key_id=telemetry_key_id,
            telemetry_payload_hash=telemetry_payload_hash,
            telemetry_algorithm=self.PLACEHOLDER_ALGORITHM,
            expected_payload_hash=telemetry_payload_hash or '',
        )

    def compute_location_payload_hash(self, payload) -> str:
        return self._hash_dict(
            {
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
                'trust_signals': {
                    'device_trust_status': payload.trust_signals.device_trust_status,
                    'device_trust_summary': payload.trust_signals.device_trust_summary,
                    'device_trust_reasons': payload.trust_signals.device_trust_reasons,
                    'integrity_status': payload.trust_signals.integrity_status,
                    'integrity_trusted': payload.trust_signals.integrity_trusted,
                    'integrity_token_present': payload.trust_signals.integrity_token_present,
                    'app_debug_build': payload.trust_signals.app_debug_build,
                    'app_debuggable': payload.trust_signals.app_debuggable,
                    'root_suspicion': payload.trust_signals.root_suspicion,
                    'mock_location_suspicion': payload.trust_signals.mock_location_suspicion,
                    'key_hardware_backed': payload.trust_signals.key_hardware_backed,
                    'attestation_declared': payload.trust_signals.attestation_declared,
                } if payload.trust_signals is not None else None,
                'integrity_verdict': payload.integrity_verdict,
                'ip_address': payload.ip_address,
            }
        )

    def compute_checkin_payload_hash(self, payload) -> str:
        signal_entries = [
            {
                'method': signal.method.value,
                'latitude': signal.latitude,
                'longitude': signal.longitude,
                'accuracy_meters': signal.accuracy_meters,
                'captured_at': signal.captured_at.isoformat(),
                'is_approximate': signal.is_approximate,
                'method_label': signal.method_label,
            }
            for signal in payload.signals
        ]
        return self._hash_dict(
            {
                'device_id': str(payload.device_id),
                'mode': payload.mode.value,
                'checkin_at': payload.checkin_at.isoformat(),
                'battery_percent': payload.battery_percent,
                'integrity_token': payload.integrity_token,
                'signals': signal_entries,
            }
        )

    def compute_command_ack_payload_hash(self, *, command_id: UUID, payload) -> str:
        return self._hash_dict(
            {
                'command_id': str(command_id),
                'org_id': str(payload.org_id),
                'device_id': str(payload.device_id),
                'key_id': payload.key_id,
                'status': payload.status.value,
                'error_message': payload.error_message,
                'metadata': payload.metadata,
            }
        )

    def _hash_dict(self, payload: dict) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    def _missing_signature_fields(
        self,
        *,
        telemetry_signature: str | None,
        telemetry_key_id: str | None,
        telemetry_payload_hash: str | None,
        telemetry_algorithm: str | None,
    ) -> bool:
        return not all([telemetry_signature, telemetry_key_id, telemetry_payload_hash, telemetry_algorithm])

    def _verify_placeholder_signature(
        self,
        *,
        telemetry_signature: str,
        telemetry_key_id: str,
        telemetry_payload_hash: str,
    ) -> bool:
        expected_signature = hashlib.sha256(f'{telemetry_key_id}:{telemetry_payload_hash}'.encode('utf-8')).hexdigest()
        return hmac.compare_digest(telemetry_signature, expected_signature)

    def _verify_asymmetric_signature(
        self,
        *,
        public_key_pem: str,
        telemetry_algorithm: str,
        telemetry_signature: str,
        telemetry_payload_hash: str,
    ) -> bool:
        try:
            signature_bytes = base64.b64decode(telemetry_signature, validate=True)
        except (binascii.Error, ValueError):
            return False

        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
        except ValueError:
            return False

        try:
            if telemetry_algorithm in self.ECDSA_SHA256_ALGORITHMS:
                public_key.verify(signature_bytes, telemetry_payload_hash.encode('utf-8'), ec.ECDSA(hashes.SHA256()))
                return True
            if telemetry_algorithm in self.RSA_SHA256_ALGORITHMS:
                public_key.verify(
                    signature_bytes,
                    telemetry_payload_hash.encode('utf-8'),
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
                return True
        except InvalidSignature:
            return False
        except (TypeError, ValueError):
            return False
        return False


def _is_hex_digest(value: str) -> bool:
    return bool(re.fullmatch(r'[a-fA-F0-9]{64,128}', value))

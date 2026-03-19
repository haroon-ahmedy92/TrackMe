import base64
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.config import settings
from app.services.integrity_verification_service import IntegrityVerificationService
from app.services.signed_telemetry_service import SignedTelemetryService, _is_hex_digest


class _ScalarResult:
    def __init__(self, value) -> None:
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeSession:
    def __init__(self, key_record) -> None:
        self.key_record = key_record

    async def execute(self, stmt):
        return _ScalarResult(self.key_record)


def _build_signed_key():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode('utf-8')
    key_record = SimpleNamespace(
        public_key_pem=public_key_pem,
        revoked_at=None,
        is_active=True,
        last_used_at=None,
    )
    return private_key, key_record


def _sign_hash(private_key, payload_hash: str) -> str:
    signature = private_key.sign(payload_hash.encode('utf-8'), ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(signature).decode('utf-8')


def test_integrity_verification_service_trusted_verdicts() -> None:
    service = IntegrityVerificationService()
    assessment = service.assess('MEETS_BASIC_INTEGRITY')
    assert assessment.trusted is True
    assert assessment.status == 'trusted_placeholder'


def test_integrity_verification_service_unavailable_and_untrusted() -> None:
    service = IntegrityVerificationService()

    missing = service.assess(None)
    assert missing.trusted is False
    assert missing.status == 'unavailable'

    untrusted = service.assess('DEVICE_COMPROMISED')
    assert untrusted.trusted is False
    assert untrusted.status == 'untrusted'


def test_payload_hash_format_guard() -> None:
    assert _is_hex_digest('a' * 64)
    assert _is_hex_digest('b' * 128)
    assert not _is_hex_digest('z' * 64)
    assert not _is_hex_digest('abc123')


def test_location_payload_hash_changes_when_trust_signals_change() -> None:
    service = SignedTelemetryService()
    payload = SimpleNamespace(
        org_id=uuid4(),
        device_id=uuid4(),
        mode=SimpleNamespace(value='normal'),
        idempotency_key='loc-test-1',
        captured_at=datetime.now(timezone.utc),
        latitude=-6.7924,
        longitude=39.2083,
        accuracy_meters=12.0,
        precision=SimpleNamespace(value='precise'),
        confidence_score=88,
        source_methods=['fused_last_known'],
        network_type='wifi',
        battery_percent=80,
        motion_state='still',
        trust_signals=SimpleNamespace(
            device_trust_status='trusted',
            device_trust_summary='Looks healthy',
            device_trust_reasons=[],
            integrity_status='trusted_placeholder',
            integrity_trusted=True,
            integrity_token_present=True,
            app_debug_build=False,
            app_debuggable=False,
            root_suspicion=False,
            mock_location_suspicion=False,
            key_hardware_backed=True,
            attestation_declared=True,
        ),
        integrity_verdict='TOKEN_PRESENT',
        ip_address=None,
    )
    changed = SimpleNamespace(**payload.__dict__)
    changed.trust_signals = SimpleNamespace(**payload.trust_signals.__dict__)
    changed.trust_signals.mock_location_suspicion = True

    assert service.compute_location_payload_hash(payload) != service.compute_location_payload_hash(changed)


@pytest.mark.asyncio
async def test_signed_telemetry_service_verifies_valid_ecdsa_signature() -> None:
    private_key, key_record = _build_signed_key()
    session = _FakeSession(key_record)
    service = SignedTelemetryService()
    payload_hash = 'a' * 64

    verification = await service.verify_signed_payload(
        session,
        device_id=uuid4(),
        telemetry_signature=_sign_hash(private_key, payload_hash),
        telemetry_key_id='device-key-1',
        telemetry_payload_hash=payload_hash,
        telemetry_algorithm='SHA256withECDSA',
        expected_payload_hash=payload_hash,
    )

    assert verification.accepted is True
    assert verification.verified is True
    assert verification.reason == 'verified'
    assert key_record.last_used_at is not None


@pytest.mark.asyncio
async def test_signed_telemetry_service_rejects_tampered_signature() -> None:
    private_key, key_record = _build_signed_key()
    session = _FakeSession(key_record)
    service = SignedTelemetryService()

    verification = await service.verify_signed_payload(
        session,
        device_id=uuid4(),
        telemetry_signature=_sign_hash(private_key, 'a' * 64),
        telemetry_key_id='device-key-1',
        telemetry_payload_hash='b' * 64,
        telemetry_algorithm='SHA256withECDSA',
        expected_payload_hash='b' * 64,
    )

    assert verification.accepted is False
    assert verification.reason == 'signature_mismatch'


@pytest.mark.asyncio
async def test_signed_telemetry_service_rejects_revoked_key() -> None:
    private_key, key_record = _build_signed_key()
    key_record.revoked_at = datetime.now(timezone.utc)
    session = _FakeSession(key_record)
    service = SignedTelemetryService()
    payload_hash = 'c' * 64

    verification = await service.verify_signed_payload(
        session,
        device_id=uuid4(),
        telemetry_signature=_sign_hash(private_key, payload_hash),
        telemetry_key_id='device-key-1',
        telemetry_payload_hash=payload_hash,
        telemetry_algorithm='SHA256withECDSA',
        expected_payload_hash=payload_hash,
    )

    assert verification.accepted is False
    assert verification.reason == 'revoked_device_key'


@pytest.mark.asyncio
async def test_signed_telemetry_service_allows_unsigned_payloads_in_optional_mode() -> None:
    previous_mode = settings.signed_telemetry_mode
    settings.signed_telemetry_mode = 'optional'
    try:
        service = SignedTelemetryService()
        verification = await service.verify_signed_payload(
            _FakeSession(None),
            device_id=uuid4(),
            telemetry_signature=None,
            telemetry_key_id=None,
            telemetry_payload_hash=None,
            telemetry_algorithm=None,
            expected_payload_hash='d' * 64,
        )
    finally:
        settings.signed_telemetry_mode = previous_mode

    assert verification.accepted is True
    assert verification.verified is False
    assert verification.reason == 'unsigned_optional_mode'

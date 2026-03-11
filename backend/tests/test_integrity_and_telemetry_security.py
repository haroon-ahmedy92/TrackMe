from app.services.integrity_verification_service import IntegrityVerificationService
from app.services.signed_telemetry_service import _is_hex_digest


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

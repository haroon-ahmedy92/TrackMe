from types import SimpleNamespace

from app.services.device_trust_service import DeviceTrustService


def test_device_trust_service_returns_caution_for_mock_root_signals() -> None:
    service = DeviceTrustService()

    result = service.assess_location_payload(
        trust_signals=SimpleNamespace(
            device_trust_reasons=['MOCK_LOCATION_HEURISTIC'],
            app_debug_build=False,
            app_debuggable=False,
            root_suspicion=True,
            mock_location_suspicion=True,
            integrity_trusted=False,
            integrity_status='unavailable',
        ),
        telemetry_verified=False,
        integrity_status='suspicious',
        integrity_trusted=False,
        verification_reason='signature_mismatch',
    )

    assert result.status == 'caution'
    assert 'ROOT_SUSPICION_PLACEHOLDER' in result.reasons
    assert 'MOCK_LOCATION_HEURISTIC' in result.reasons


def test_device_trust_service_returns_trusted_for_verified_signed_payload() -> None:
    service = DeviceTrustService()

    result = service.assess_location_payload(
        trust_signals=SimpleNamespace(
            device_trust_reasons=[],
            app_debug_build=False,
            app_debuggable=False,
            root_suspicion=False,
            mock_location_suspicion=False,
            integrity_trusted=True,
            integrity_status='verified',
        ),
        telemetry_verified=True,
        integrity_status='verified',
        integrity_trusted=True,
        verification_reason='verified',
    )

    assert result.status == 'trusted'
    assert result.summary.startswith('Signed telemetry')

from __future__ import annotations

import json
from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class IntegrityAssessment:
    status: str
    trusted: bool
    reason: str
    provider: str


class IntegrityVerificationService:
    """
    Advisory integrity evaluator with a migration path toward real Play Integrity verification.

    Current supported inputs:
    - raw verdict strings
    - JSON envelopes produced by a future verifier component
    """

    VERIFIED_VERDICTS = {'MEETS_DEVICE_INTEGRITY', 'MEETS_STRONG_INTEGRITY'}
    ADVISORY_VERDICTS = {'MEETS_BASIC_INTEGRITY', 'TOKEN_PRESENT'}
    UNAVAILABLE_VERDICTS = {'TOKEN_MISSING', 'UNAVAILABLE', 'UNAVAILABLE_PLACEHOLDER'}
    SUSPICIOUS_VERDICTS = {'FAILED', 'INVALID', 'REPLAYED', 'PACKAGE_MISMATCH', 'REQUEST_INVALID'}

    def __init__(self) -> None:
        self.provider = settings.integrity_verification_provider
        self.expected_package = settings.play_integrity_expected_package

    def assess(self, verdict: str | None) -> IntegrityAssessment:
        normalized = (verdict or '').strip()
        if not normalized:
            return self._result(status='unavailable', trusted=False, reason='missing_verdict', provider=self.provider or 'none')

        envelope = self._parse_envelope(normalized)
        if envelope is not None:
            return self._assess_envelope(envelope)

        upper = normalized.upper()
        if upper in self.VERIFIED_VERDICTS:
            return self._result(status='verified', trusted=True, reason='verdict_verified', provider=self.provider or 'raw')
        if upper in self.ADVISORY_VERDICTS:
            return self._result(status='advisory', trusted=False, reason='verdict_advisory', provider=self.provider or 'raw')
        if upper in self.UNAVAILABLE_VERDICTS:
            return self._result(status='unavailable', trusted=False, reason='verdict_unavailable', provider=self.provider or 'raw')
        if upper in self.SUSPICIOUS_VERDICTS:
            return self._result(status='suspicious', trusted=False, reason='verdict_suspicious', provider=self.provider or 'raw')
        return self._result(status='advisory', trusted=False, reason='verdict_unknown', provider=self.provider or 'raw')

    def _assess_envelope(self, envelope: dict) -> IntegrityAssessment:
        provider = str(envelope.get('provider') or self.provider or 'envelope')
        if provider not in {'play_integrity', 'play_integrity_envelope', 'none'}:
            return self._result(status='advisory', trusted=False, reason='unsupported_provider', provider=provider)

        package_name = envelope.get('package_name') or envelope.get('packageName')
        if self.expected_package and package_name and package_name != self.expected_package:
            return self._result(status='suspicious', trusted=False, reason='package_mismatch', provider=provider)

        explicit_status = str(envelope.get('status') or '').strip().lower()
        if explicit_status in {'verified', 'advisory', 'unavailable', 'suspicious'}:
            return self._result(
                status=explicit_status,
                trusted=explicit_status == 'verified',
                reason=str(envelope.get('reason') or f'{explicit_status}_envelope'),
                provider=provider,
            )

        device_verdicts = envelope.get('deviceRecognitionVerdict') or envelope.get('device_recognition_verdict') or []
        if not isinstance(device_verdicts, list):
            device_verdicts = [str(device_verdicts)]
        verdict_set = {str(item).upper() for item in device_verdicts}
        if verdict_set & self.VERIFIED_VERDICTS:
            return self._result(status='verified', trusted=True, reason='device_integrity_verified', provider=provider)
        if verdict_set & self.ADVISORY_VERDICTS:
            return self._result(status='advisory', trusted=False, reason='basic_integrity_only', provider=provider)

        request_details = envelope.get('requestDetails') or envelope.get('request_details') or {}
        if isinstance(request_details, dict):
            request_package = request_details.get('requestPackageName')
            if self.expected_package and request_package and request_package != self.expected_package:
                return self._result(status='suspicious', trusted=False, reason='request_package_mismatch', provider=provider)

        return self._result(status='unavailable', trusted=False, reason='envelope_incomplete', provider=provider)

    def _parse_envelope(self, verdict: str) -> dict | None:
        if not verdict.startswith('{'):
            return None
        try:
            parsed = json.loads(verdict)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _result(self, *, status: str, trusted: bool, reason: str, provider: str) -> IntegrityAssessment:
        return IntegrityAssessment(status=status, trusted=trusted, reason=reason, provider=provider)

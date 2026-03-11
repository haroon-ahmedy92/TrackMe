from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrityAssessment:
    status: str
    trusted: bool
    reason: str


class IntegrityVerificationService:
    """
    Play Integrity placeholder evaluator.

    This does not call Google APIs directly; it classifies integrity verdict strings supplied
    by trusted upstream verification components and returns a normalized trust decision.
    """

    TRUSTED_VERDICTS = {
        'MEETS_DEVICE_INTEGRITY',
        'MEETS_STRONG_INTEGRITY',
        'MEETS_BASIC_INTEGRITY',
        'TOKEN_PRESENT',
    }

    def assess(self, verdict: str | None) -> IntegrityAssessment:
        normalized = (verdict or '').strip().upper()
        if not normalized:
            return IntegrityAssessment(status='unavailable', trusted=False, reason='missing_verdict')
        if normalized in self.TRUSTED_VERDICTS:
            return IntegrityAssessment(status='trusted_placeholder', trusted=True, reason='trusted_verdict')
        if normalized in {'UNAVAILABLE_PLACEHOLDER', 'TOKEN_MISSING'}:
            return IntegrityAssessment(status='unavailable', trusted=False, reason='token_unavailable')
        return IntegrityAssessment(status='untrusted', trusted=False, reason='verdict_not_trusted')

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceTrustAssessment:
    status: str
    summary: str
    reasons: list[str]
    root_suspicion: bool
    debug_suspicion: bool
    mock_location_suspicion: bool
    integrity_status: str
    integrity_trusted: bool
    telemetry_verified: bool


class DeviceTrustService:
    """
    Produces advisory device-trust summaries.

    These checks are intentionally cautious. They help operators spot unusual telemetry without
    claiming cryptographic certainty or hidden compromise detection.
    """

    def assess_location_payload(
        self,
        *,
        trust_signals,
        telemetry_verified: bool,
        integrity_status: str,
        integrity_trusted: bool,
        verification_reason: str,
    ) -> DeviceTrustAssessment:
        reasons: list[str] = []
        root_suspicion = False
        debug_suspicion = False
        mock_location_suspicion = False

        if trust_signals is not None:
            root_suspicion = trust_signals.root_suspicion
            debug_suspicion = trust_signals.app_debuggable or trust_signals.app_debug_build
            mock_location_suspicion = trust_signals.mock_location_suspicion
            reasons.extend(trust_signals.device_trust_reasons)
            if not trust_signals.integrity_trusted and trust_signals.integrity_status:
                reasons.append(f'CLIENT_INTEGRITY_{trust_signals.integrity_status.upper()}')

        if not telemetry_verified:
            reasons.append(f'TELEMETRY_{verification_reason.upper()}')
        if not integrity_trusted:
            reasons.append(f'BACKEND_INTEGRITY_{integrity_status.upper()}')
        if root_suspicion:
            reasons.append('ROOT_SUSPICION_PLACEHOLDER')
        if debug_suspicion:
            reasons.append('DEBUG_BUILD_OR_DEBUGGABLE')
        if mock_location_suspicion:
            reasons.append('MOCK_LOCATION_HEURISTIC')

        reasons = sorted(set(reason for reason in reasons if reason))

        if any(
            reason.startswith('ROOT_')
            or reason.startswith('MOCK_')
            or reason.endswith('UNTRUSTED')
            or reason == 'DEBUG_BUILD_OR_DEBUGGABLE'
            for reason in reasons
        ):
            return DeviceTrustAssessment(
                status='caution',
                summary='Advisory trust signals suggest operator review. This is not proof of compromise.',
                reasons=reasons,
                root_suspicion=root_suspicion,
                debug_suspicion=debug_suspicion,
                mock_location_suspicion=mock_location_suspicion,
                integrity_status=integrity_status,
                integrity_trusted=integrity_trusted,
                telemetry_verified=telemetry_verified,
            )

        if telemetry_verified or integrity_trusted:
            return DeviceTrustAssessment(
                status='trusted',
                summary='Signed telemetry and current advisory signals look consistent.',
                reasons=reasons,
                root_suspicion=root_suspicion,
                debug_suspicion=debug_suspicion,
                mock_location_suspicion=mock_location_suspicion,
                integrity_status=integrity_status,
                integrity_trusted=integrity_trusted,
                telemetry_verified=telemetry_verified,
            )

        return DeviceTrustAssessment(
            status='unavailable',
            summary='Trust-signal coverage is limited. Treat this as unknown rather than safe or compromised.',
            reasons=reasons,
            root_suspicion=root_suspicion,
            debug_suspicion=debug_suspicion,
            mock_location_suspicion=mock_location_suspicion,
            integrity_status=integrity_status,
            integrity_trusted=integrity_trusted,
            telemetry_verified=telemetry_verified,
        )

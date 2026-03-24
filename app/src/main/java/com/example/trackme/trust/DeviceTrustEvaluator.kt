package com.example.trackme.trust

import com.example.trackme.domain.model.LocationSnapshot
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
open class DeviceTrustEvaluator @Inject constructor() {
    open fun assess(
        integritySignal: IntegritySignal,
        appSignals: AppTrustSignals,
        locationSnapshot: LocationSnapshot?,
        keyHardwareBacked: Boolean,
        attestationDeclared: Boolean,
    ): DeviceTrustSummary {
        val reasons = buildList {
            if (appSignals.debugBuild) add("DEBUG_BUILD_PLACEHOLDER")
            if (appSignals.debuggableApp) add("DEBUGGABLE_APP_FLAG")
            if (appSignals.rootSuspicion) add("ROOT_SUSPICION_PLACEHOLDER")
            if (locationSnapshot?.suspiciousMockLocation == true) add("MOCK_LOCATION_HEURISTIC")
            if (integritySignal.status.equals("suspicious", ignoreCase = true)) {
                add("INTEGRITY_SUSPICIOUS")
            }
            if (!integritySignal.trusted && integritySignal.status.equals("advisory", ignoreCase = true)) {
                add("INTEGRITY_ADVISORY")
            }
            if (!integritySignal.trusted && integritySignal.status.equals("untrusted", ignoreCase = true)) {
                add("INTEGRITY_NOT_TRUSTED")
            }
            if (!integritySignal.trusted && integritySignal.status.equals("unavailable", ignoreCase = true)) {
                add("INTEGRITY_UNAVAILABLE")
            }
        }.distinct()

        val status = when {
            reasons.any {
                it == "ROOT_SUSPICION_PLACEHOLDER" ||
                    it == "MOCK_LOCATION_HEURISTIC" ||
                    it == "INTEGRITY_NOT_TRUSTED" ||
                    it == "INTEGRITY_SUSPICIOUS" ||
                    it == "DEBUGGABLE_APP_FLAG"
            } -> DeviceTrustStatus.CAUTION

            integritySignal.trusted || keyHardwareBacked -> DeviceTrustStatus.TRUSTED
            else -> DeviceTrustStatus.UNAVAILABLE
        }

        val headline = when (status) {
            DeviceTrustStatus.TRUSTED -> "Advisory trust signals look healthy"
            DeviceTrustStatus.CAUTION -> "Some trust signals deserve operator review"
            DeviceTrustStatus.UNAVAILABLE -> "Trust signal coverage is limited"
        }
        val details = when (status) {
            DeviceTrustStatus.TRUSTED ->
                "Signed telemetry and current device signals do not show obvious issues. This is advisory, not proof."
            DeviceTrustStatus.CAUTION ->
                "One or more advisory checks looked unusual. Treat this as a caution signal, not confirmed compromise."
            DeviceTrustStatus.UNAVAILABLE ->
                "The app does not have enough trustworthy signals yet to make a stronger advisory assessment."
        }

        return DeviceTrustSummary(
            status = status,
            headline = headline,
            details = details,
            reasons = reasons,
            integrityStatus = integritySignal.status,
            integrityTrusted = integritySignal.trusted,
            debugBuild = appSignals.debugBuild,
            debuggableApp = appSignals.debuggableApp,
            rootSuspicion = appSignals.rootSuspicion,
            mockLocationSuspicion = locationSnapshot?.suspiciousMockLocation == true,
            keyHardwareBacked = keyHardwareBacked,
            attestationDeclared = attestationDeclared,
            integrityTokenPresent = !integritySignal.token.isNullOrBlank(),
        )
    }
}

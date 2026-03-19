package com.example.trackme.trust

enum class DeviceTrustStatus {
    TRUSTED,
    CAUTION,
    UNAVAILABLE,
}

data class IntegritySignal(
    val token: String?,
    val status: String,
    val trusted: Boolean,
    val provider: String,
)

data class AppTrustSignals(
    val debugBuild: Boolean,
    val debuggableApp: Boolean,
    val testKeysBuild: Boolean,
    val suBinaryPresent: Boolean,
) {
    val rootSuspicion: Boolean
        get() = testKeysBuild || suBinaryPresent
}

data class DeviceTrustSummary(
    val status: DeviceTrustStatus,
    val headline: String,
    val details: String,
    val reasons: List<String>,
    val integrityStatus: String,
    val integrityTrusted: Boolean,
    val debugBuild: Boolean,
    val debuggableApp: Boolean,
    val rootSuspicion: Boolean,
    val mockLocationSuspicion: Boolean,
    val keyHardwareBacked: Boolean,
    val attestationDeclared: Boolean,
    val integrityTokenPresent: Boolean,
)

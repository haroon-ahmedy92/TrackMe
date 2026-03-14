package com.example.trackme.compliance

import javax.inject.Inject

/**
 * Single source of truth for consent/legal copy shown during enrollment.
 * This ensures all tracking-relevant disclosures stay explicit and consistent.
 */
data class ConsentDisclosure(
    val version: String,
    val title: String,
    val bulletPoints: List<String>
)

interface CompliancePolicy {
    fun enrollmentDisclosure(): ConsentDisclosure
}

class DefaultCompliancePolicy @Inject constructor() : CompliancePolicy {
    override fun enrollmentDisclosure(): ConsentDisclosure {
        return ConsentDisclosure(
            version = "2026-03-15",
            title = "Organization Device Recovery Disclosure",
            bulletPoints = listOf(
                "This app is visible and intended for organization-owned or explicitly enrolled devices.",
                "Location/check-in collection only runs after explicit enrollment consent.",
                "Background location is requested only because recovery and last-known-location features need lawful updates when the app is not open.",
                "Approximate sources such as network or IP-derived context are labeled as approximate and must not be treated as exact recovery coordinates.",
                "No covert recording, screenshots, camera, or microphone capture is performed.",
                "Lost mode uses time-boxed higher-frequency updates and a visible in-app indicator.",
                "Every sensitive action, including locate requests and policy changes, is recorded in an audit trail."
            )
        )
    }
}

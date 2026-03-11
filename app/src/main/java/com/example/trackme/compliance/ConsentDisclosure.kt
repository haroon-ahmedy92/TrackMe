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
            version = "2026-03-10",
            title = "Organization Device Recovery Disclosure",
            bulletPoints = listOf(
                "This app is visible and intended for organization-owned or explicitly enrolled devices.",
                "Location/check-in collection only runs after explicit enrollment consent.",
                "No covert recording, screenshots, camera, or microphone capture is performed.",
                "Lost mode uses time-boxed higher-frequency updates and a visible in-app indicator.",
                "All significant actions are written to a local append-only audit trail."
            )
        )
    }
}

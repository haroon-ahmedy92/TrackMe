package com.example.trackme.feature.status

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.R
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.feature.common.ChipRow
import com.example.trackme.feature.common.EmptyStateCard
import com.example.trackme.feature.common.ManagedStateBanner
import com.example.trackme.feature.common.MetricRow
import com.example.trackme.feature.common.SectionCard
import com.example.trackme.feature.common.StatusChip
import com.example.trackme.feature.common.TrackMeScreen
import com.example.trackme.ui.common.formatEpochMillis

@Composable
fun DeviceStatusScreen(
    viewModel: DeviceStatusViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    TrackMeScreen(
        title = stringResource(id = R.string.device_status_title),
        subtitle = "Consent, enrollment timing, and recovery telemetry quality."
    ) {
        ManagedStateBanner()

        when (val state = uiState) {
            AsyncUiState.Loading -> EmptyStateCard(
                title = "Loading status",
                body = stringResource(id = R.string.loading)
            )
            is AsyncUiState.Error -> EmptyStateCard(
                title = "Status unavailable",
                body = state.message
            )
            is AsyncUiState.Data -> {
                val dashboard = state.value
                SectionCard(
                    title = "Enrollment",
                    eyebrow = "Governance"
                ) {
                    MetricRow(label = "Consent version", value = dashboard.enrollment.consentVersion ?: "-")
                    MetricRow(label = "Enrolled at", value = formatEpochMillis(dashboard.enrollment.enrolledAtEpochMs))
                    MetricRow(label = "Ownership type", value = dashboard.enrollment.ownershipType?.name?.replace('_', ' ') ?: "-")
                    MetricRow(label = "Authorized by", value = dashboard.enrollment.authorizationRole?.name?.replace('_', ' ') ?: "-")
                    MetricRow(label = "Owner subject", value = dashboard.enrollment.ownerSubject ?: "Not bound on-device")
                    MetricRow(label = "Pairing method", value = dashboard.enrollment.pairingMethod?.name?.replace('_', ' ') ?: "-")
                    MetricRow(label = "Registration state", value = dashboard.enrollment.registrationState.name.replace('_', ' '))
                    MetricRow(label = "Lost mode until", value = formatEpochMillis(dashboard.deviceState.lostModeUntilEpochMs))
                }

                SectionCard(
                    title = "Recovery telemetry",
                    eyebrow = "Location quality"
                ) {
                    val location = dashboard.lastLocation
                    if (location == null) {
                        MetricRow(label = "Last location", value = "No sample collected yet")
                    } else {
                        ChipRow(
                            {
                                StatusChip(
                                    label = if (location.isApproximate) "Approximate source" else "Higher-confidence source",
                                    containerColor = if (location.isApproximate) {
                                        MaterialTheme.colorScheme.tertiaryContainer
                                    } else {
                                        MaterialTheme.colorScheme.primaryContainer
                                    },
                                    contentColor = if (location.isApproximate) {
                                        MaterialTheme.colorScheme.onTertiaryContainer
                                    } else {
                                        MaterialTheme.colorScheme.onPrimaryContainer
                                    }
                                )
                            },
                            {
                                StatusChip(
                                    label = "${location.confidenceScore}/100 confidence",
                                    containerColor = MaterialTheme.colorScheme.secondaryContainer,
                                    contentColor = MaterialTheme.colorScheme.onSecondaryContainer
                                )
                            }
                        )
                        MetricRow(label = "Method", value = location.methodLabel, emphasize = true)
                        MetricRow(label = "Timestamp", value = formatEpochMillis(location.capturedAtEpochMs))
                        MetricRow(label = "Precision", value = if (location.isApproximate) "Approximate" else "Moderate or precise")
                    }
                }
            }
        }
    }
}

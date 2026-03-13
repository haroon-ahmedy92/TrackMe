package com.example.trackme.feature.home

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.R
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.feature.common.ChipRow
import com.example.trackme.feature.common.EmptyStateCard
import com.example.trackme.feature.common.InfoCallout
import com.example.trackme.feature.common.ManagedStateBanner
import com.example.trackme.feature.common.MetricRow
import com.example.trackme.feature.common.SectionCard
import com.example.trackme.feature.common.StatusChip
import com.example.trackme.feature.common.TrackMeScreen
import com.example.trackme.ui.common.formatEpochMillis

@Composable
fun HomeDashboardScreen(
    viewModel: HomeViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    TrackMeScreen(
        title = stringResource(id = R.string.home_title),
        subtitle = "A quick view of enrollment, battery, and recovery readiness."
    ) {
        ManagedStateBanner()

        when (val state = uiState) {
            AsyncUiState.Loading -> EmptyStateCard(
                title = "Preparing dashboard",
                body = stringResource(id = R.string.loading)
            )
            is AsyncUiState.Error -> EmptyStateCard(
                title = "Dashboard unavailable",
                body = state.message
            )
            is AsyncUiState.Data -> {
                val dashboard = state.value
                SectionCard(
                    title = "Device snapshot",
                    eyebrow = "Overview"
                ) {
                    ChipRow(
                        {
                            StatusChip(
                                label = dashboard.deviceState.mode.name,
                                containerColor = androidx.compose.material3.MaterialTheme.colorScheme.primaryContainer,
                                contentColor = androidx.compose.material3.MaterialTheme.colorScheme.onPrimaryContainer
                            )
                        },
                        {
                            StatusChip(
                                label = dashboard.enrollment.organizationName ?: "Not assigned",
                                containerColor = androidx.compose.material3.MaterialTheme.colorScheme.secondaryContainer,
                                contentColor = androidx.compose.material3.MaterialTheme.colorScheme.onSecondaryContainer
                            )
                        }
                    )
                    MetricRow(
                        label = "Organization",
                        value = dashboard.enrollment.organizationName ?: "-"
                    )
                    MetricRow(
                        label = "Last check-in",
                        value = formatEpochMillis(dashboard.deviceState.lastCheckInEpochMs),
                        emphasize = true
                    )
                    MetricRow(
                        label = "Mode",
                        value = dashboard.deviceState.mode.name
                    )
                    MetricRow(
                        label = "Battery",
                        value = dashboard.deviceState.batteryPercent?.let { "$it%" } ?: "-"
                    )
                    MetricRow(
                        label = "Ownership",
                        value = dashboard.enrollment.ownershipType?.name?.replace('_', ' ') ?: "-"
                    )
                    MetricRow(
                        label = "Registration",
                        value = dashboard.enrollment.registrationState.name.replace('_', ' ')
                    )
                }

                InfoCallout(
                    text = "Lost mode should only be enabled during an active recovery incident. The device remains visibly managed while enrolled."
                )

                dashboard.lastLocation?.let { location ->
                    SectionCard(
                        title = "Last known location",
                        eyebrow = "Location"
                    ) {
                        MetricRow(label = "Method", value = location.methodLabel)
                        MetricRow(
                            label = "Confidence",
                            value = "${location.confidenceScore}/100",
                            emphasize = true
                        )
                        MetricRow(
                            label = "Coordinates",
                            value = "${location.latitude}, ${location.longitude}"
                        )
                        StatusChip(
                            label = if (location.isApproximate) "Approximate" else "Precise source",
                            containerColor = if (location.isApproximate) {
                                androidx.compose.material3.MaterialTheme.colorScheme.tertiaryContainer
                            } else {
                                androidx.compose.material3.MaterialTheme.colorScheme.primaryContainer
                            },
                            contentColor = if (location.isApproximate) {
                                androidx.compose.material3.MaterialTheme.colorScheme.onTertiaryContainer
                            } else {
                                androidx.compose.material3.MaterialTheme.colorScheme.onPrimaryContainer
                            }
                        )
                    }
                }
            }
        }
    }
}

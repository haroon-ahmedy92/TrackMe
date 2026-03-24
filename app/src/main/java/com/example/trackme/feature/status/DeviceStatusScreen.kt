package com.example.trackme.feature.status

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.R
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.model.LocationPrecision
import com.example.trackme.feature.common.ChipRow
import com.example.trackme.feature.common.EmptyStateCard
import com.example.trackme.feature.common.LocationFreshness
import com.example.trackme.feature.common.ManagedStateBanner
import com.example.trackme.feature.common.MetricRow
import com.example.trackme.feature.common.SectionCard
import com.example.trackme.feature.common.StatusChip
import com.example.trackme.feature.common.TrackMeScreen
import com.example.trackme.feature.common.freshness
import com.example.trackme.trust.DeviceTrustStatus
import com.example.trackme.ui.common.formatEpochMillis

@Composable
fun DeviceStatusScreen(
    viewModel: DeviceStatusViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    TrackMeScreen(
        title = stringResource(id = R.string.device_status_title),
        subtitle = stringResource(id = R.string.device_status_subtitle)
    ) {
        ManagedStateBanner()

        when (val state = uiState) {
            AsyncUiState.Loading -> EmptyStateCard(
                title = stringResource(id = R.string.loading_status_title),
                body = stringResource(id = R.string.loading)
            )
            is AsyncUiState.Error -> EmptyStateCard(
                title = stringResource(id = R.string.status_unavailable_title),
                body = state.message
            )
            is AsyncUiState.Data -> {
                val dashboard = state.value
                SectionCard(
                    title = stringResource(id = R.string.enrollment_section_title),
                    eyebrow = stringResource(id = R.string.governance_label)
                ) {
                    MetricRow(
                        label = stringResource(id = R.string.consent_version_metric_label),
                        value = dashboard.enrollment.consentVersion ?: "-"
                    )
                    MetricRow(
                        label = stringResource(id = R.string.enrolled_at_metric_label),
                        value = formatEpochMillis(dashboard.enrollment.enrolledAtEpochMs)
                    )
                    MetricRow(label = stringResource(id = R.string.ownership_type_label), value = dashboard.enrollment.ownershipType?.name?.replace('_', ' ') ?: "-")
                    MetricRow(label = stringResource(id = R.string.authorized_by_metric_label), value = dashboard.enrollment.authorizationRole?.name?.replace('_', ' ') ?: "-")
                    MetricRow(label = stringResource(id = R.string.owner_subject_metric_label), value = dashboard.enrollment.ownerSubject ?: stringResource(id = R.string.owner_subject_not_bound))
                    MetricRow(label = stringResource(id = R.string.pairing_method_metric_label), value = dashboard.enrollment.pairingMethod?.name?.replace('_', ' ') ?: "-")
                    MetricRow(label = stringResource(id = R.string.registration_state_label), value = dashboard.enrollment.registrationState.name.replace('_', ' '))
                    MetricRow(
                        label = stringResource(id = R.string.lost_mode_until_metric_label),
                        value = formatEpochMillis(dashboard.deviceState.lostModeUntilEpochMs)
                    )
                }

                SectionCard(
                    title = stringResource(id = R.string.trust_signals_title),
                    eyebrow = stringResource(id = R.string.advisory_label)
                ) {
                    val trust = dashboard.trustSummary
                    ChipRow(
                        {
                            StatusChip(
                                label = when (trust.status) {
                                    DeviceTrustStatus.TRUSTED -> stringResource(id = R.string.trusted_signals_label)
                                    DeviceTrustStatus.CAUTION -> stringResource(id = R.string.needs_review_label)
                                    DeviceTrustStatus.UNAVAILABLE -> stringResource(id = R.string.signals_limited_label)
                                },
                                containerColor = when (trust.status) {
                                    DeviceTrustStatus.TRUSTED -> MaterialTheme.colorScheme.primaryContainer
                                    DeviceTrustStatus.CAUTION -> MaterialTheme.colorScheme.tertiaryContainer
                                    DeviceTrustStatus.UNAVAILABLE -> MaterialTheme.colorScheme.surfaceVariant
                                },
                                contentColor = when (trust.status) {
                                    DeviceTrustStatus.TRUSTED -> MaterialTheme.colorScheme.onPrimaryContainer
                                    DeviceTrustStatus.CAUTION -> MaterialTheme.colorScheme.onTertiaryContainer
                                    DeviceTrustStatus.UNAVAILABLE -> MaterialTheme.colorScheme.onSurfaceVariant
                                }
                            )
                        },
                        {
                            StatusChip(
                                label = if (trust.integrityTrusted) {
                                    stringResource(id = R.string.integrity_trusted_label)
                                } else {
                                    stringResource(id = R.string.integrity_limited_label)
                                },
                                containerColor = MaterialTheme.colorScheme.secondaryContainer,
                                contentColor = MaterialTheme.colorScheme.onSecondaryContainer
                            )
                        }
                    )
                    MetricRow(label = stringResource(id = R.string.summary_label), value = trust.headline, emphasize = true)
                    MetricRow(label = stringResource(id = R.string.details_label), value = trust.details)
                    MetricRow(label = stringResource(id = R.string.root_suspicion_label), value = if (trust.rootSuspicion) stringResource(id = R.string.observed_label) else stringResource(id = R.string.not_observed_label))
                    MetricRow(label = stringResource(id = R.string.mock_location_label), value = if (trust.mockLocationSuspicion) stringResource(id = R.string.observed_label) else stringResource(id = R.string.not_observed_label))
                    MetricRow(label = stringResource(id = R.string.debuggable_app_label), value = if (trust.debuggableApp) stringResource(id = R.string.observed_label) else stringResource(id = R.string.not_observed_label))
                    MetricRow(label = stringResource(id = R.string.hardware_backed_key_label), value = if (trust.keyHardwareBacked) stringResource(id = R.string.declared_label) else stringResource(id = R.string.not_declared_label))
                    MetricRow(
                        label = stringResource(id = R.string.reasons_label),
                        value = if (trust.reasons.isEmpty()) stringResource(id = R.string.no_additional_trust_reasons) else trust.reasons.joinToString()
                    )
                }

                SectionCard(
                    title = stringResource(id = R.string.recovery_telemetry_title),
                    eyebrow = stringResource(id = R.string.location_quality_label)
                ) {
                    val location = dashboard.lastLocation
                    if (location == null) {
                        MetricRow(label = stringResource(id = R.string.last_location_label), value = stringResource(id = R.string.no_sample_collected))
                    } else {
                        val freshness = location.freshness()
                        ChipRow(
                            {
                                StatusChip(
                                    label = when (location.precision) {
                                        LocationPrecision.PRECISE -> stringResource(id = R.string.label_precise)
                                        LocationPrecision.MODERATE -> stringResource(id = R.string.label_moderate)
                                        LocationPrecision.APPROXIMATE -> stringResource(id = R.string.label_approximate)
                                    },
                                    containerColor = if (location.isApproximate) MaterialTheme.colorScheme.tertiaryContainer else MaterialTheme.colorScheme.primaryContainer,
                                    contentColor = if (location.isApproximate) MaterialTheme.colorScheme.onTertiaryContainer else MaterialTheme.colorScheme.onPrimaryContainer
                                )
                            },
                            {
                                StatusChip(
                                    label = stringResource(id = R.string.confidence_chip, location.confidenceScore),
                                    containerColor = MaterialTheme.colorScheme.secondaryContainer,
                                    contentColor = MaterialTheme.colorScheme.onSecondaryContainer
                                )
                            },
                            {
                                StatusChip(
                                    label = when (freshness) {
                                        LocationFreshness.RECENT -> stringResource(id = R.string.label_live_recent)
                                        LocationFreshness.STALE -> stringResource(id = R.string.label_stale)
                                        LocationFreshness.OFFLINE -> stringResource(id = R.string.label_offline)
                                    },
                                    containerColor = MaterialTheme.colorScheme.surfaceVariant,
                                    contentColor = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        )
                        MetricRow(
                            label = stringResource(id = R.string.method_metric_label),
                            value = location.methodLabel
                        )
                        MetricRow(label = stringResource(id = R.string.timestamp_label), value = formatEpochMillis(location.capturedAtEpochMs))
                        MetricRow(
                            label = stringResource(id = R.string.precision_label),
                            value = when (location.precision) {
                                LocationPrecision.PRECISE -> stringResource(id = R.string.label_precise)
                                LocationPrecision.MODERATE -> stringResource(id = R.string.label_moderate)
                                LocationPrecision.APPROXIMATE -> stringResource(id = R.string.label_approximate)
                            }
                        )
                        MetricRow(
                            label = stringResource(id = R.string.network_state_label),
                            value = location.networkType.name.lowercase().replaceFirstChar { it.uppercase() }
                        )
                        MetricRow(
                            label = stringResource(id = R.string.sample_state_label),
                            value = when (freshness) {
                                LocationFreshness.RECENT -> stringResource(id = R.string.label_live_recent)
                                LocationFreshness.STALE -> stringResource(id = R.string.label_stale)
                                LocationFreshness.OFFLINE -> stringResource(id = R.string.label_offline)
                            }
                        )
                        if (location.isApproximate) {
                            MetricRow(
                                label = stringResource(id = R.string.source_approximate_label),
                                value = stringResource(id = R.string.source_not_exact_label)
                            )
                        }
                    }
                }
            }
        }
    }
}

package com.example.trackme.feature.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.R
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.feature.common.EmptyStateCard
import com.example.trackme.feature.common.InfoCallout
import com.example.trackme.feature.common.ManagedStateBanner
import com.example.trackme.feature.common.MetricRow
import com.example.trackme.feature.common.SectionCard
import com.example.trackme.feature.common.SectionDivider
import com.example.trackme.feature.common.StatusChip
import com.example.trackme.feature.common.TrackMeScreen
import com.example.trackme.ui.common.formatEpochMillis

@Composable
fun SettingsPrivacyScreen(
    viewModel: SettingsPrivacyViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val abuseDraft = remember { mutableStateOf("") }
    val deprovisionReason = remember { mutableStateOf("") }

    TrackMeScreen(
        title = stringResource(id = R.string.settings_privacy_title),
        subtitle = stringResource(id = R.string.settings_privacy_subtitle)
    ) {
        ManagedStateBanner()
        InfoCallout(text = stringResource(id = R.string.settings_privacy_disclosure))

        when (val state = uiState) {
            AsyncUiState.Loading -> EmptyStateCard(
                title = stringResource(id = R.string.loading_privacy_settings_title),
                body = stringResource(id = R.string.loading)
            )
            is AsyncUiState.Error -> EmptyStateCard(
                title = stringResource(id = R.string.settings_unavailable_title),
                body = state.message
            )
            is AsyncUiState.Data -> {
                val content = state.value
                SectionCard(
                    title = stringResource(id = R.string.consent_record_title),
                    eyebrow = stringResource(id = R.string.visible_enrollment_label)
                ) {
                    StatusChip(
                        label = if (content.consentVersion != null) {
                            stringResource(id = R.string.consent_recorded_label)
                        } else {
                            stringResource(id = R.string.consent_missing_label)
                        },
                        containerColor = if (content.consentVersion != null) {
                            MaterialTheme.colorScheme.secondaryContainer
                        } else {
                            MaterialTheme.colorScheme.tertiaryContainer
                        },
                        contentColor = if (content.consentVersion != null) {
                            MaterialTheme.colorScheme.onSecondaryContainer
                        } else {
                            MaterialTheme.colorScheme.onTertiaryContainer
                        }
                    )
                    MetricRow(
                        label = stringResource(id = R.string.onboarding_consent_record_label),
                        value = content.consentVersion ?: stringResource(id = R.string.not_recorded_label)
                    )
                    MetricRow(
                        label = stringResource(id = R.string.accepted_at_label),
                        value = formatEpochMillis(content.consentAcceptedAtEpochMs)
                    )
                    Text(
                        text = stringResource(id = R.string.background_location_core_feature_body),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                SectionCard(
                    title = stringResource(id = R.string.privacy_dashboard_title),
                    eyebrow = stringResource(id = R.string.policy_safe_defaults_label)
                ) {
                    MetricRow(label = stringResource(id = R.string.app_visibility_label), value = stringResource(id = R.string.always_visible_value))
                    MetricRow(label = stringResource(id = R.string.locate_access_label), value = stringResource(id = R.string.reason_required_value))
                    MetricRow(label = stringResource(id = R.string.approximate_signals_label), value = stringResource(id = R.string.important_approximate_value), emphasize = true)
                    MetricRow(label = stringResource(id = R.string.retention_default_label), value = stringResource(id = R.string.short_admin_controlled_value))
                    MetricRow(label = stringResource(id = R.string.sensitive_actions_metric_label), value = stringResource(id = R.string.explained_before_use_value))
                }

                SectionCard(
                    title = stringResource(id = R.string.geofence_protection_title),
                    eyebrow = stringResource(id = R.string.opt_in_asset_protection_label)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = stringResource(id = R.string.geofence_opt_in),
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.weight(1f)
                        )
                        Switch(
                            checked = content.geofenceEnabled,
                            onCheckedChange = viewModel::onGeofenceToggle
                        )
                    }

                    StatusChip(
                        label = if (content.geofenceEnabled) {
                            stringResource(id = R.string.protection_enabled_label)
                        } else {
                            stringResource(id = R.string.protection_disabled_label)
                        },
                        containerColor = if (content.geofenceEnabled) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surfaceVariant,
                        contentColor = if (content.geofenceEnabled) MaterialTheme.colorScheme.onSecondaryContainer else MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    MetricRow(
                        label = stringResource(id = R.string.radius_label),
                        value = "${content.geofenceRadiusMeters} meters",
                        emphasize = true
                    )

                    Slider(
                        value = content.geofenceRadiusMeters.toFloat(),
                        onValueChange = { viewModel.onRadiusChange(it.toInt().coerceIn(100, 2000)) },
                        valueRange = 100f..2000f
                    )

                    Text(
                        text = stringResource(id = R.string.geofence_explanation_body),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                SectionCard(
                    title = stringResource(id = R.string.access_history_title),
                    eyebrow = stringResource(id = R.string.owner_admin_visibility_label)
                ) {
                    if (content.accessHistory.isEmpty()) {
                        Text(
                            text = stringResource(id = R.string.no_access_history),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            content.accessHistory.forEachIndexed { index, item ->
                                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                    Text(
                                        text = item.title,
                                        style = MaterialTheme.typography.titleMedium,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                    Text(
                                        text = item.summary,
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                    Text(
                                        text = formatEpochMillis(item.createdAtEpochMs),
                                        style = MaterialTheme.typography.labelMedium,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                }
                                if (index != content.accessHistory.lastIndex) {
                                    SectionDivider()
                                }
                            }
                        }
                    }
                }

                SectionCard(
                    title = stringResource(id = R.string.report_abuse_title),
                    eyebrow = stringResource(id = R.string.support_accountability_label)
                ) {
                    Text(
                        text = stringResource(id = R.string.report_abuse_body),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    OutlinedTextField(
                        value = abuseDraft.value,
                        onValueChange = { abuseDraft.value = it },
                        label = { Text(stringResource(id = R.string.what_happened_label)) },
                        supportingText = { Text(stringResource(id = R.string.abuse_report_supporting)) },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 3
                    )
                    Button(
                        onClick = {
                            viewModel.submitAbuseReport(abuseDraft.value)
                            abuseDraft.value = ""
                        },
                        enabled = abuseDraft.value.trim().length >= 8,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(stringResource(id = R.string.submit_abuse_report))
                    }
                }

                SectionCard(
                    title = stringResource(id = R.string.deprovision_title),
                    eyebrow = stringResource(id = R.string.authorized_removal_label)
                ) {
                    Text(
                        text = stringResource(id = R.string.deprovision_body),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    OutlinedTextField(
                        value = deprovisionReason.value,
                        onValueChange = { deprovisionReason.value = it },
                        label = { Text(stringResource(id = R.string.deprovision_reason_label)) },
                        supportingText = { Text(stringResource(id = R.string.deprovision_reason_supporting)) },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 2
                    )
                    Button(
                        onClick = {
                            viewModel.requestDeprovision(deprovisionReason.value)
                            deprovisionReason.value = ""
                        },
                        enabled = deprovisionReason.value.trim().length >= 8,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(stringResource(id = R.string.request_deprovision))
                    }
                }

                InfoCallout(text = stringResource(id = R.string.retention_console_callout))
                content.statusMessage?.let {
                    Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

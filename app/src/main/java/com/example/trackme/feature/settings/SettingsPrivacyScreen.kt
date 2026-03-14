package com.example.trackme.feature.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
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
        subtitle = "Clear privacy controls for visible recovery features."
    ) {
        ManagedStateBanner()
        InfoCallout(text = stringResource(id = R.string.settings_privacy_disclosure))

        when (val state = uiState) {
            AsyncUiState.Loading -> EmptyStateCard(
                title = "Loading privacy settings",
                body = stringResource(id = R.string.loading)
            )
            is AsyncUiState.Error -> EmptyStateCard(
                title = "Settings unavailable",
                body = state.message
            )
            is AsyncUiState.Data -> {
                val content = state.value
                SectionCard(
                    title = "Consent record",
                    eyebrow = "Visible enrollment"
                ) {
                    StatusChip(
                        label = if (content.consentVersion != null) "Consent recorded" else "Consent record missing",
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
                        label = "Consent version",
                        value = content.consentVersion ?: "Not recorded"
                    )
                    MetricRow(
                        label = "Accepted at",
                        value = formatEpochMillis(content.consentAcceptedAtEpochMs)
                    )
                    Text(
                        text = "Background location is explained during onboarding because last-known-location recovery is a core feature. This app does not enable hidden or deceptive behavior.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                SectionCard(
                    title = "Privacy dashboard",
                    eyebrow = "Policy-safe defaults"
                ) {
                    MetricRow(label = "App visibility", value = "Always visible")
                    MetricRow(label = "Locate access", value = "Reason required and audited")
                    MetricRow(label = "Approximate signals", value = "Clearly labeled", emphasize = true)
                    MetricRow(label = "Retention default", value = "Short and admin-controlled")
                    MetricRow(label = "Sensitive actions", value = "Explained before use")
                }

                SectionCard(
                    title = "Geofence protection",
                    eyebrow = "Opt-in asset protection"
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
                        label = if (content.geofenceEnabled) "Protection enabled" else "Protection disabled",
                        containerColor = if (content.geofenceEnabled) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surfaceVariant,
                        contentColor = if (content.geofenceEnabled) MaterialTheme.colorScheme.onSecondaryContainer else MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    MetricRow(
                        label = "Radius",
                        value = "${content.geofenceRadiusMeters} meters",
                        emphasize = true
                    )

                    Slider(
                        value = content.geofenceRadiusMeters.toFloat(),
                        onValueChange = { viewModel.onRadiusChange(it.toInt().coerceIn(100, 2000)) },
                        valueRange = 100f..2000f
                    )

                    Text(
                        text = "Geofence alerts are optional asset-protection signals. They complement location evidence and are not a replacement for explicit consent or platform policy checks.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                SectionCard(
                    title = "Access history",
                    eyebrow = "Owner and admin visibility"
                ) {
                    if (content.accessHistory.isEmpty()) {
                        Text(
                            text = "No recent access activity has been recorded on this device yet.",
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
                    title = "Report abuse or confusion",
                    eyebrow = "Support and accountability"
                ) {
                    Text(
                        text = "If someone used the product in a way that seems inconsistent with policy, report it here. Reports are added to the audit trail for follow-up.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    OutlinedTextField(
                        value = abuseDraft.value,
                        onValueChange = { abuseDraft.value = it },
                        label = { Text("What happened?") },
                        supportingText = { Text("Describe the misuse, confusion, or unexpected access behavior.") },
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
                        Text("Submit abuse report")
                    }
                }

                SectionCard(
                    title = "Account deletion / deprovision",
                    eyebrow = "Authorized removal"
                ) {
                    Text(
                        text = "Use this flow when the device should no longer remain enrolled or managed. Final deprovisioning should be completed by an authorized admin workflow so the action is fully audited.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    OutlinedTextField(
                        value = deprovisionReason.value,
                        onValueChange = { deprovisionReason.value = it },
                        label = { Text("Reason for deprovision") },
                        supportingText = { Text("For example: device returned to stock, user offboarded, or consent withdrawn.") },
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
                        Text("Request deprovision")
                    }
                }

                InfoCallout(text = "Tenant retention settings are kept short by default and should only be changed by authorized admins in the web console.")
                content.statusMessage?.let {
                    Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

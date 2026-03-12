package com.example.trackme.feature.incidents

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
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
import com.example.trackme.feature.common.StatusChip
import com.example.trackme.feature.common.TrackMeScreen
import com.example.trackme.ui.common.formatEpochMillis

@Composable
fun IncidentsScreen(
    viewModel: IncidentsViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    when (val state = uiState) {
        AsyncUiState.Loading -> TrackMeScreen(
            title = stringResource(id = R.string.incidents_title),
            subtitle = stringResource(id = R.string.incidents_description)
        ) {
            EmptyStateCard(title = "Loading incidents", body = stringResource(id = R.string.loading))
        }

        is AsyncUiState.Error -> TrackMeScreen(
            title = stringResource(id = R.string.incidents_title),
            subtitle = stringResource(id = R.string.incidents_description)
        ) {
            EmptyStateCard(title = "Incident controls unavailable", body = state.message)
        }

        is AsyncUiState.Data -> {
            val content = state.value

            TrackMeScreen(
                title = stringResource(id = R.string.incidents_title),
                subtitle = stringResource(id = R.string.incidents_description)
            ) {
                ManagedStateBanner()

                SectionCard(
                    title = "Incident summary",
                    eyebrow = "Current state"
                ) {
                    StatusChip(
                        label = content.incidentState.name,
                        containerColor = MaterialTheme.colorScheme.primaryContainer,
                        contentColor = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    MetricRow(
                        label = "Lost-mode window",
                        value = formatEpochMillis(content.lostModeUntilEpochMs)
                    )
                    MetricRow(
                        label = "Scheduled wipe",
                        value = formatEpochMillis(content.wipeScheduledAtEpochMs)
                    )
                    content.statusMessage?.let {
                        Text(text = it, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }

                content.recoveryMessage.takeIf { it.isNotBlank() }?.let { message ->
                    InfoCallout(text = message)
                }

                SectionCard(
                    title = "Recovery details",
                    eyebrow = "Authorization"
                ) {
                    OutlinedTextField(
                        value = content.ticketReference,
                        onValueChange = viewModel::onTicketChanged,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text(stringResource(id = R.string.ticket_reference)) }
                    )
                    OutlinedTextField(
                        value = content.recoveryMessage,
                        onValueChange = viewModel::onRecoveryMessageChanged,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text(stringResource(id = R.string.recovery_message_label)) }
                    )
                    OutlinedTextField(
                        value = content.elevatedConfirmationText,
                        onValueChange = viewModel::onElevatedConfirmationChanged,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text(stringResource(id = R.string.elevated_confirmation_label)) }
                    )
                    Text(
                        text = stringResource(id = R.string.elevated_confirmation_hint),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    OutlinedTextField(
                        value = content.wipeReason,
                        onValueChange = viewModel::onWipeReasonChanged,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text(stringResource(id = R.string.incident_action_reason_label)) }
                    )
                    OutlinedTextField(
                        value = content.wipeDelayMinutes,
                        onValueChange = viewModel::onWipeDelayChanged,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text(stringResource(id = R.string.wipe_delay_minutes_label)) }
                    )
                    RowCheckbox(
                        checked = content.acknowledgedWipeTradeoff,
                        onCheckedChange = viewModel::onAcknowledgeTradeoffChanged,
                        label = stringResource(id = R.string.wipe_tradeoff_ack_label)
                    )
                    RowCheckbox(
                        checked = content.confirmedWipeIntent,
                        onCheckedChange = viewModel::onConfirmWipeIntentChanged,
                        label = stringResource(id = R.string.wipe_confirm_ack_label)
                    )
                }

                SectionCard(
                    title = "Sensitive actions",
                    eyebrow = "Visible workflow"
                ) {
                    Button(
                        onClick = viewModel::markAsLost,
                        enabled = !content.inProgress,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(stringResource(id = R.string.start_lost_incident))
                    }
                    Button(
                        onClick = viewModel::confirmStolen,
                        enabled = !content.inProgress,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(stringResource(id = R.string.confirm_stolen_incident))
                    }
                    Button(
                        onClick = viewModel::requestRemoteLock,
                        enabled = !content.inProgress,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(stringResource(id = R.string.request_remote_lock))
                    }
                    Button(
                        onClick = viewModel::requestRemoteWipe,
                        enabled = !content.inProgress,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(stringResource(id = R.string.request_remote_wipe))
                    }
                    OutlinedButton(
                        onClick = viewModel::recover,
                        enabled = !content.inProgress,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(stringResource(id = R.string.mark_recovered))
                    }
                    OutlinedButton(
                        onClick = viewModel::cancelIncident,
                        enabled = !content.inProgress,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(stringResource(id = R.string.cancel_incident))
                    }
                    OutlinedButton(
                        onClick = viewModel::decommission,
                        enabled = !content.inProgress,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(stringResource(id = R.string.decommission_device))
                    }
                }

                InfoCallout(text = stringResource(id = R.string.wipe_tradeoff_text))
                InfoCallout(text = stringResource(id = R.string.remote_action_policy_note))

                SectionCard(
                    title = stringResource(id = R.string.evidence_timeline_label),
                    eyebrow = "Audit-backed history"
                ) {
                    if (content.timeline.isEmpty()) {
                        Text(
                            text = "No incident events yet.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        content.timeline.forEach { event ->
                            SectionCard(
                                modifier = Modifier.fillMaxWidth(),
                                title = "${event.action} (${event.state.name})",
                                eyebrow = formatEpochMillis(event.createdAtEpochMs)
                            ) {
                                Text(text = event.summary)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun RowCheckbox(
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    label: String
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Checkbox(checked = checked, onCheckedChange = onCheckedChange)
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium
        )
    }
}

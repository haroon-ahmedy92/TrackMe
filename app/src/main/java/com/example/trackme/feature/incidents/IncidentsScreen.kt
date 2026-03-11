package com.example.trackme.feature.incidents

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
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
import com.example.trackme.feature.common.ManagedStateBanner
import com.example.trackme.ui.common.formatEpochMillis

@Composable
fun IncidentsScreen(
    viewModel: IncidentsViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    when (val state = uiState) {
        AsyncUiState.Loading -> Text(stringResource(id = R.string.loading))
        is AsyncUiState.Error -> Text(state.message, color = MaterialTheme.colorScheme.error)
        is AsyncUiState.Data -> {
            val content = state.value

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                ManagedStateBanner()
                Text(text = stringResource(id = R.string.incidents_title), style = MaterialTheme.typography.headlineSmall)
                Text(text = stringResource(id = R.string.incidents_description))
                Text(
                    text = stringResource(id = R.string.incident_state_label, content.incidentState.name),
                    color = MaterialTheme.colorScheme.primary
                )

                content.recoveryMessage.takeIf { it.isNotBlank() }?.let { message ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(stringResource(id = R.string.visible_recovery_message_title))
                            Text(message)
                        }
                    }
                }

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
                    style = MaterialTheme.typography.bodySmall
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

                Text(
                    text = stringResource(id = R.string.wipe_tradeoff_text),
                    color = MaterialTheme.colorScheme.secondary
                )
                Text(
                    text = stringResource(id = R.string.remote_action_policy_note),
                    color = MaterialTheme.colorScheme.secondary
                )
                Text(
                    text = stringResource(id = R.string.incident_lost_until_label, formatEpochMillis(content.lostModeUntilEpochMs))
                )
                Text(
                    text = stringResource(id = R.string.incident_wipe_scheduled_label, formatEpochMillis(content.wipeScheduledAtEpochMs))
                )
                content.statusMessage?.let { Text(it) }

                HorizontalDivider()
                Text(
                    text = stringResource(id = R.string.evidence_timeline_label),
                    style = MaterialTheme.typography.titleMedium
                )
                LazyColumn(
                    modifier = Modifier
                        .fillMaxWidth()
                        .fillMaxHeight(),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(content.timeline, key = { it.id }) { event ->
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text("${event.action} (${event.state.name})", style = MaterialTheme.typography.labelLarge)
                                Text(event.summary)
                                Text(formatEpochMillis(event.createdAtEpochMs), style = MaterialTheme.typography.bodySmall)
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
        Text(label)
    }
}

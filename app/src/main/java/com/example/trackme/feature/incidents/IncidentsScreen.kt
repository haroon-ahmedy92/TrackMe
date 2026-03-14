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
import com.example.trackme.feature.common.SectionDivider
import com.example.trackme.feature.common.StatusChip
import com.example.trackme.feature.common.TrackMeScreen
import com.example.trackme.domain.model.IncidentEvidenceExportFormat
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
                    content.lastKnownLocation?.let { lastLocation ->
                        MetricRow(
                            label = "Last known location",
                            value = "${lastLocation.methodLabel} • ${lastLocation.confidenceScore}/100"
                        )
                        MetricRow(
                            label = "Location precision",
                            value = if (lastLocation.isApproximate) "Approximate" else lastLocation.precision.name
                        )
                        MetricRow(
                            label = "Location timestamp",
                            value = formatEpochMillis(lastLocation.capturedAtEpochMs)
                        )
                        lastLocation.geofenceTransition?.let { transition ->
                            MetricRow(label = "Geofence alert", value = transition.replaceFirstChar { it.uppercase() })
                        }
                    }
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
                    title = "Case notes",
                    eyebrow = "Editable analyst notes"
                ) {
                    OutlinedTextField(
                        value = content.noteDraft,
                        onValueChange = viewModel::onNoteDraftChanged,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("Note for this case") }
                    )
                    RowCheckbox(
                        checked = content.notePinned,
                        onCheckedChange = viewModel::onNotePinnedChanged,
                        label = "Pin note to top of case view"
                    )
                    Button(
                        onClick = viewModel::addCaseNote,
                        enabled = !content.inProgress,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Save case note")
                    }
                    if (content.notes.isEmpty()) {
                        Text(
                            text = "No analyst notes yet. Notes stay separate from the immutable audit log.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        content.notes.forEach { note ->
                            SectionCard(
                                modifier = Modifier.fillMaxWidth(),
                                title = if (note.isPinned) "Pinned note" else "Analyst note",
                                eyebrow = formatEpochMillis(note.updatedAtEpochMs)
                            ) {
                                Text(text = note.body)
                                Text(
                                    text = "Author: ${note.authorLabel}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }

                SectionCard(
                    title = "Attachments and export",
                    eyebrow = "Case package support"
                ) {
                    InfoCallout(
                        text = "Android records attachment references and export placeholders. Full evidence packages are assembled on the backend or web console."
                    )
                    OutlinedTextField(
                        value = content.attachmentNameDraft,
                        onValueChange = viewModel::onAttachmentNameDraftChanged,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("Attachment name") }
                    )
                    OutlinedTextField(
                        value = content.attachmentDescriptionDraft,
                        onValueChange = viewModel::onAttachmentDescriptionDraftChanged,
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("Attachment note") }
                    )
                    Button(
                        onClick = viewModel::addAttachmentReference,
                        enabled = !content.inProgress,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Record attachment reference")
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Button(
                            onClick = { viewModel.requestEvidenceExport(IncidentEvidenceExportFormat.JSON) },
                            enabled = !content.inProgress,
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("JSON export")
                        }
                        OutlinedButton(
                            onClick = { viewModel.requestEvidenceExport(IncidentEvidenceExportFormat.PDF) },
                            enabled = !content.inProgress,
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("PDF export")
                        }
                    }
                    if (content.attachments.isNotEmpty()) {
                        SectionDivider()
                        content.attachments.forEach { attachment ->
                            MetricRow(
                                label = attachment.fileName,
                                value = formatEpochMillis(attachment.createdAtEpochMs)
                            )
                            attachment.description?.let {
                                Text(
                                    text = it,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                    if (content.evidenceExports.isNotEmpty()) {
                        SectionDivider()
                        content.evidenceExports.forEach { export ->
                            MetricRow(
                                label = "${export.format.name} export placeholder",
                                value = formatEpochMillis(export.createdAtEpochMs)
                            )
                            Text(
                                text = export.redactionSummary,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }

                SectionCard(
                    title = "Actions taken during recovery",
                    eyebrow = "Commands and decisions"
                ) {
                    if (content.actionsTaken.isEmpty()) {
                        Text(
                            text = "No remote command attempts recorded yet.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        content.actionsTaken.forEach { action ->
                            SectionCard(
                                modifier = Modifier.fillMaxWidth(),
                                title = action.type.name.replace('_', ' '),
                                eyebrow = formatEpochMillis(action.executedAtEpochMs ?: action.requestedAtEpochMs)
                            ) {
                                Text(text = "${action.status.name} • ${action.reason}")
                                Text(
                                    text = "Actor: ${action.requestedBy}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                action.lastError?.let {
                                    Text(
                                        text = "Last error: $it",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.error
                                    )
                                }
                            }
                        }
                    }
                }

                SectionCard(
                    title = "Chain of events",
                    eyebrow = "Immutable evidence plus mutable notes"
                ) {
                    if (content.evidenceChain.isEmpty()) {
                        Text(
                            text = "No case evidence entries yet.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        content.evidenceChain.forEach { entry ->
                            SectionCard(
                                modifier = Modifier.fillMaxWidth(),
                                title = entry.title,
                                eyebrow = formatEpochMillis(entry.occurredAtEpochMs)
                            ) {
                                Text(text = entry.summary)
                                Text(
                                    text = "Type: ${entry.kind.name.replace('_', ' ')}${entry.actorLabel?.let { " • $it" } ?: ""}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                if (entry.mutable) {
                                    Text(
                                        text = "Editable note entry",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                }
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

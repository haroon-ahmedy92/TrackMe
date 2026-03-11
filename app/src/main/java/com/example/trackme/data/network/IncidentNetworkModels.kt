package com.example.trackme.data.network

import kotlinx.serialization.Serializable
import kotlinx.serialization.SerialName
import kotlinx.serialization.json.JsonElement

@Serializable
data class IncidentRecordResponseDto(
    @SerialName("incident_id") val incidentId: String,
    @SerialName("device_id") val deviceId: String,
    @SerialName("ticket_reference") val ticketReference: String,
    val state: String,
    @SerialName("recovery_message") val recoveryMessage: String,
    @SerialName("wipe_scheduled_at") val wipeScheduledAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String
)

@Serializable
data class IncidentTimelineEventDto(
    val id: String,
    @SerialName("incident_id") val incidentId: String,
    val state: String,
    val action: String,
    val summary: String,
    val metadata: Map<String, JsonElement> = emptyMap(),
    @SerialName("occurred_at") val occurredAt: String
)

@Serializable
data class MarkDeviceLostRequestDto(
    @SerialName("device_id") val deviceId: String,
    @SerialName("ticket_reference") val ticketReference: String,
    @SerialName("recovery_message") val recoveryMessage: String,
    @SerialName("lost_mode_window_hours") val lostModeWindowHours: Int = 12
)

@Serializable
data class ConfirmStolenRequestDto(
    val reason: String,
    @SerialName("elevated_confirmation") val elevatedConfirmation: Boolean
)

@Serializable
data class RemoteLockDecisionRequestDto(
    val reason: String
)

@Serializable
data class RemoteWipeDecisionRequestDto(
    val reason: String,
    @SerialName("elevated_confirmation") val elevatedConfirmation: Boolean,
    @SerialName("confirm_wipe_intent") val confirmWipeIntent: Boolean,
    @SerialName("acknowledge_tradeoff") val acknowledgeTradeoff: Boolean,
    @SerialName("delay_minutes") val delayMinutes: Int
)

@Serializable
data class IncidentResolutionRequestDto(
    val reason: String
)

@Serializable
data class IncidentRemoteActionResponseDto(
    @SerialName("action_id") val actionId: String? = null,
    val status: String? = null,
    @SerialName("incident_id") val incidentId: String? = null,
    val state: String? = null,
    @SerialName("wipe_scheduled_at") val wipeScheduledAt: String? = null
)

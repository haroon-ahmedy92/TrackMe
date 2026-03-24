package com.example.trackme.data.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

/**
 * Live API contract shared with the FastAPI backend.
 *
 * The base URL is expected to end with `/api/`, for example:
 * - `http://10.0.2.2:8000/api/` for Android emulator local backend access
 * - `http://192.168.1.50:8000/api/` for a physical device on the same LAN
 */
interface RecoveryApi {
    @POST("v1/telemetry/check-ins")
    suspend fun submitCheckIn(@Body request: CheckInRequest)

    @POST("v1/platform/locations/ingest-batch")
    suspend fun ingestLocationsBatch(
        @Body request: LocationIngestBatchRequestDto
    ): LocationIngestBatchResponseDto

    @POST("v1/ownership/pairings/complete")
    suspend fun completePairing(@Body request: PairingCompleteRequestDto): OwnershipBindingResponseDto


    @POST("v1/commands/device-tokens")
    suspend fun registerDevicePushToken(
        @Body request: DevicePushTokenRegistrationRequestDto
    )

    @POST("v1/commands/sync")
    suspend fun syncPendingCommands(
        @Body request: DeviceCommandSyncRequestDto
    ): List<CommandEnvelopeDto>

    @POST("v1/commands/{commandId}/ack")
    suspend fun acknowledgeCommand(
        @Path("commandId") commandId: String,
        @Body request: CommandAckRequestDto
    )

    @POST("v1/incidents/mark-lost")
    suspend fun markDeviceLost(@Body request: MarkDeviceLostRequestDto): IncidentRecordResponseDto

    @POST("v1/incidents/{incidentId}/confirm-stolen")
    suspend fun confirmStolen(
        @Path("incidentId") incidentId: String,
        @Body request: ConfirmStolenRequestDto
    ): IncidentRecordResponseDto

    @POST("v1/incidents/{incidentId}/remote-lock")
    suspend fun requestRemoteLockDecision(
        @Path("incidentId") incidentId: String,
        @Body request: RemoteLockDecisionRequestDto
    ): IncidentRemoteActionResponseDto

    @POST("v1/incidents/{incidentId}/remote-wipe")
    suspend fun requestRemoteWipeDecision(
        @Path("incidentId") incidentId: String,
        @Body request: RemoteWipeDecisionRequestDto
    ): IncidentRemoteActionResponseDto

    @POST("v1/incidents/{incidentId}/recover")
    suspend fun markRecovered(
        @Path("incidentId") incidentId: String,
        @Body request: IncidentResolutionRequestDto
    ): IncidentRecordResponseDto

    @POST("v1/incidents/{incidentId}/cancel")
    suspend fun cancelIncident(
        @Path("incidentId") incidentId: String,
        @Body request: IncidentResolutionRequestDto
    ): IncidentRecordResponseDto

    @POST("v1/incidents/{incidentId}/decommission")
    suspend fun decommissionDevice(
        @Path("incidentId") incidentId: String,
        @Body request: IncidentResolutionRequestDto
    ): IncidentRecordResponseDto

    @GET("v1/incidents/{incidentId}/timeline")
    suspend fun getIncidentTimeline(
        @Path("incidentId") incidentId: String
    ): List<IncidentTimelineEventDto>
}

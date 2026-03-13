package com.example.trackme.data.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

/**
 * Backend-ready API surface. Endpoints are intentionally minimal placeholders for MVP scaffolding.
 */
interface RecoveryApi {
    @POST("v1/check-ins")
    suspend fun submitCheckIn(@Body request: CheckInRequest)

    @POST("v1/audit-events")
    suspend fun submitAuditEvent(@Body request: AuditEventRequest)

    @POST("v1/ownership/pairings/complete")
    suspend fun completePairing(@Body request: PairingCompleteRequestDto): OwnershipBindingResponseDto

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

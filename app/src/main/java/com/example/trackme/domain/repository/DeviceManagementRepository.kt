package com.example.trackme.domain.repository

/**
 * Hook surface for org-managed device actions.
 * MVP keeps this explicit and backend-configurable; no bypass/local privilege escalation.
 */
interface DeviceManagementRepository {
    suspend fun requestRemoteLock(ticketReference: String): Result<Unit>
    suspend fun requestRemoteWipe(ticketReference: String): Result<Unit>
}

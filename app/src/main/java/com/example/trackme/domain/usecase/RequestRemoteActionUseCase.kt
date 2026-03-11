package com.example.trackme.domain.usecase

import com.example.trackme.domain.repository.AuditRepository
import com.example.trackme.domain.repository.DeviceCapabilityRepository
import com.example.trackme.domain.repository.DeviceManagementRepository
import javax.inject.Inject

class RequestRemoteActionUseCase @Inject constructor(
    private val deviceManagementRepository: DeviceManagementRepository,
    private val capabilityRepository: DeviceCapabilityRepository,
    private val auditRepository: AuditRepository
) {
    suspend fun requestLock(ticketReference: String): Result<Unit> {
        if (!capabilityRepository.supportsPolicyManagedRemoteActions()) {
            auditRepository.appendEvent(
                type = "REMOTE_LOCK_BLOCKED",
                summary = "Remote lock blocked: device is not policy-managed",
                metadata = mapOf("ticketReference" to ticketReference)
            )
            return Result.failure(
                IllegalStateException("Remote lock is only allowed on policy-managed devices.")
            )
        }

        val result = deviceManagementRepository.requestRemoteLock(ticketReference)
        auditRepository.appendEvent(
            type = "REMOTE_LOCK_REQUESTED",
            summary = "Remote lock hook invoked",
            metadata = mapOf(
                "ticketReference" to ticketReference,
                "result" to (if (result.isSuccess) "success" else "failure")
            )
        )
        return result
    }

    suspend fun requestWipe(ticketReference: String): Result<Unit> {
        if (!capabilityRepository.supportsPolicyManagedRemoteActions()) {
            auditRepository.appendEvent(
                type = "REMOTE_WIPE_BLOCKED",
                summary = "Remote wipe blocked: device is not policy-managed",
                metadata = mapOf("ticketReference" to ticketReference)
            )
            return Result.failure(
                IllegalStateException("Remote wipe is only allowed on policy-managed devices.")
            )
        }

        val result = deviceManagementRepository.requestRemoteWipe(ticketReference)
        auditRepository.appendEvent(
            type = "REMOTE_WIPE_REQUESTED",
            summary = "Remote wipe hook invoked",
            metadata = mapOf(
                "ticketReference" to ticketReference,
                "result" to (if (result.isSuccess) "success" else "failure")
            )
        )
        return result
    }
}

package com.example.trackme.data.repository

import com.example.trackme.domain.repository.DeviceManagementRepository
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DeviceManagementRepositoryImpl @Inject constructor() : DeviceManagementRepository {

    override suspend fun requestRemoteLock(ticketReference: String): Result<Unit> {
        return Result.failure(
            IllegalStateException("Remote lock hook is not configured for this deployment.")
        )
    }

    override suspend fun requestRemoteWipe(ticketReference: String): Result<Unit> {
        return Result.failure(
            IllegalStateException("Remote wipe hook is not configured for this deployment.")
        )
    }
}

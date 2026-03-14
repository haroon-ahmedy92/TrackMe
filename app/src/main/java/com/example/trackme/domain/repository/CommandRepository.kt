package com.example.trackme.domain.repository

import com.example.trackme.domain.model.DeviceCommand
import com.example.trackme.domain.model.DeviceCommandStatus
import kotlinx.coroutines.flow.Flow

interface CommandRepository {
    fun observeCommands(): Flow<List<DeviceCommand>>
    suspend fun registerPushToken(pushToken: String, appVersion: String? = null)
    suspend fun syncPendingCommands()
    suspend fun flushPendingAcknowledgements()
    suspend fun getOpenCommands(): List<DeviceCommand>
    suspend fun updateLocalStatus(commandId: String, status: DeviceCommandStatus, lastError: String? = null)
    suspend fun acknowledgeCommand(commandId: String, status: DeviceCommandStatus, lastError: String? = null, metadata: Map<String, String> = emptyMap())
}

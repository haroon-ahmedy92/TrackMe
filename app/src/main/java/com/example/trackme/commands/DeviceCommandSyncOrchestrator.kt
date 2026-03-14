package com.example.trackme.commands

import com.example.trackme.domain.repository.CommandRepository
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DeviceCommandSyncOrchestrator @Inject constructor(
    private val commandRepository: CommandRepository,
    private val pendingCommandProcessor: PendingCommandProcessor,
) {
    suspend fun syncAndProcess() {
        commandRepository.flushPendingAcknowledgements()
        commandRepository.syncPendingCommands()
        pendingCommandProcessor.processPendingCommands()
        commandRepository.flushPendingAcknowledgements()
    }
}

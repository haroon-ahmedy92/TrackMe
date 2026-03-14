package com.example.trackme.commands

import com.example.trackme.domain.model.DeviceCommand
import com.example.trackme.domain.model.DeviceCommandStatus
import com.example.trackme.domain.repository.CommandRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

class DeviceCommandSyncOrchestratorTest {

    @Test
    fun syncAndProcess_flushes_before_and_after_processing() = runTest {
        val events = mutableListOf<String>()
        val repository = FakeCommandRepository(events)
        val processor = FakePendingCommandProcessor(events)
        val orchestrator = DeviceCommandSyncOrchestrator(repository, processor)

        orchestrator.syncAndProcess()

        assertEquals(
            listOf("flush", "sync", "process", "flush"),
            events
        )
    }
}

private class FakePendingCommandProcessor(
    private val events: MutableList<String>
) : PendingCommandProcessor {
    override suspend fun processPendingCommands() {
        events += "process"
    }
}

private class FakeCommandRepository(
    private val events: MutableList<String>
) : CommandRepository {
    override fun observeCommands(): Flow<List<DeviceCommand>> = flowOf(emptyList())

    override suspend fun registerPushToken(pushToken: String, appVersion: String?) = Unit

    override suspend fun syncPendingCommands() {
        events += "sync"
    }

    override suspend fun flushPendingAcknowledgements() {
        events += "flush"
    }

    override suspend fun getOpenCommands(): List<DeviceCommand> = emptyList()

    override suspend fun updateLocalStatus(commandId: String, status: DeviceCommandStatus, lastError: String?) = Unit

    override suspend fun acknowledgeCommand(
        commandId: String,
        status: DeviceCommandStatus,
        lastError: String?,
        metadata: Map<String, String>
    ) = Unit
}

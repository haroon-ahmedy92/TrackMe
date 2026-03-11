package com.example.trackme.domain.usecase

import com.example.trackme.domain.model.AuditEvent
import com.example.trackme.domain.repository.AuditRepository
import com.example.trackme.domain.repository.DeviceCapabilityRepository
import com.example.trackme.domain.repository.DeviceManagementRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertTrue
import org.junit.Test

class RequestRemoteActionUseCaseTest {

    @Test
    fun `requestLock is blocked when device is not policy managed`() = runBlocking {
        val useCase = RequestRemoteActionUseCase(
            deviceManagementRepository = FakeDeviceManagementRepository(),
            capabilityRepository = FakeDeviceCapabilityRepository(isManaged = false),
            auditRepository = FakeAuditRepository()
        )

        val result = useCase.requestLock(ticketReference = "INC-001")

        assertTrue(result.isFailure)
    }

    private class FakeDeviceCapabilityRepository(
        private val isManaged: Boolean
    ) : DeviceCapabilityRepository {
        override fun supportsPolicyManagedRemoteActions(): Boolean = isManaged
    }

    private class FakeDeviceManagementRepository : DeviceManagementRepository {
        override suspend fun requestRemoteLock(ticketReference: String): Result<Unit> = Result.success(Unit)
        override suspend fun requestRemoteWipe(ticketReference: String): Result<Unit> = Result.success(Unit)
    }

    private class FakeAuditRepository : AuditRepository {
        override fun observeRecentEvents(limit: Int): Flow<List<AuditEvent>> = flowOf(emptyList())
        override suspend fun appendEvent(type: String, summary: String, metadata: Map<String, String>) = Unit
    }
}

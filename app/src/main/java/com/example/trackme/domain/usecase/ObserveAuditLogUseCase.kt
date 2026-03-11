package com.example.trackme.domain.usecase

import com.example.trackme.domain.model.AuditEvent
import com.example.trackme.domain.repository.AuditRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class ObserveAuditLogUseCase @Inject constructor(
    private val auditRepository: AuditRepository
) {
    operator fun invoke(limit: Int = 100): Flow<List<AuditEvent>> = auditRepository.observeRecentEvents(limit)
}

package com.example.trackme.domain.repository

import com.example.trackme.domain.model.AuditEvent
import kotlinx.coroutines.flow.Flow

interface AuditRepository {
    fun observeRecentEvents(limit: Int = 100): Flow<List<AuditEvent>>
    suspend fun appendEvent(type: String, summary: String, metadata: Map<String, String> = emptyMap())
}

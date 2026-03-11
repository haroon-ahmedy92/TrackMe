package com.example.trackme.domain.repository

import com.example.trackme.domain.model.IncidentRecord
import com.example.trackme.domain.model.IncidentTimelineEntry
import kotlinx.coroutines.flow.Flow

interface IncidentRepository {
    fun observeCurrentIncident(): Flow<IncidentRecord>
    fun observeTimeline(limit: Int = 200): Flow<List<IncidentTimelineEntry>>
    suspend fun getCurrentIncident(): IncidentRecord
    suspend fun upsertCurrentIncident(record: IncidentRecord)
    suspend fun appendTimelineEntry(entry: IncidentTimelineEntry)
}

package com.example.trackme.data.repository

import com.example.trackme.data.local.dao.IncidentDao
import com.example.trackme.data.local.entity.IncidentStateEntity
import com.example.trackme.data.local.entity.IncidentTimelineEntity
import com.example.trackme.domain.model.IncidentRecord
import com.example.trackme.domain.model.IncidentState
import com.example.trackme.domain.model.IncidentTimelineEntry
import com.example.trackme.domain.repository.IncidentRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class IncidentRepositoryImpl @Inject constructor(
    private val incidentDao: IncidentDao
) : IncidentRepository {

    override fun observeCurrentIncident(): Flow<IncidentRecord> {
        return incidentDao.observeCurrent().map { entity -> entity?.toDomain() ?: IncidentRecord() }
    }

    override fun observeTimeline(limit: Int): Flow<List<IncidentTimelineEntry>> {
        return incidentDao.observeTimeline(limit).map { rows -> rows.map { it.toDomain() } }
    }

    override suspend fun getCurrentIncident(): IncidentRecord {
        return incidentDao.getCurrent()?.toDomain() ?: IncidentRecord()
    }

    override suspend fun upsertCurrentIncident(record: IncidentRecord) {
        incidentDao.upsertCurrent(
            IncidentStateEntity(
                id = IncidentStateEntity.SINGLETON_ID,
                incidentId = record.incidentId,
                state = record.state.name,
                ticketReference = record.ticketReference,
                recoveryMessage = record.recoveryMessage,
                createdAtEpochMs = record.createdAtEpochMs,
                updatedAtEpochMs = record.updatedAtEpochMs,
                lostModeUntilEpochMs = record.lostModeUntilEpochMs,
                wipeScheduledAtEpochMs = record.wipeScheduledAtEpochMs,
                pendingWipeReason = record.pendingWipeReason
            )
        )
    }

    override suspend fun appendTimelineEntry(entry: IncidentTimelineEntry) {
        incidentDao.insertTimeline(
            IncidentTimelineEntity(
                incidentId = entry.incidentId,
                state = entry.state.name,
                action = entry.action,
                summary = entry.summary,
                metadataJson = entry.metadataJson,
                createdAtEpochMs = entry.createdAtEpochMs
            )
        )
    }

    private fun IncidentStateEntity.toDomain(): IncidentRecord {
        return IncidentRecord(
            incidentId = incidentId,
            state = runCatching { IncidentState.valueOf(state) }.getOrDefault(IncidentState.NORMAL),
            ticketReference = ticketReference,
            recoveryMessage = recoveryMessage,
            createdAtEpochMs = createdAtEpochMs,
            updatedAtEpochMs = updatedAtEpochMs,
            lostModeUntilEpochMs = lostModeUntilEpochMs,
            wipeScheduledAtEpochMs = wipeScheduledAtEpochMs,
            pendingWipeReason = pendingWipeReason
        )
    }

    private fun IncidentTimelineEntity.toDomain(): IncidentTimelineEntry {
        return IncidentTimelineEntry(
            id = id,
            incidentId = incidentId,
            state = runCatching { IncidentState.valueOf(state) }.getOrDefault(IncidentState.NORMAL),
            action = action,
            summary = summary,
            metadataJson = metadataJson,
            createdAtEpochMs = createdAtEpochMs
        )
    }
}

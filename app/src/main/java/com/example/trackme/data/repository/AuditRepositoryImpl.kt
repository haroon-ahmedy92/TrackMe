package com.example.trackme.data.repository

import com.example.trackme.core.Hasher
import com.example.trackme.core.TimeProvider
import com.example.trackme.data.local.dao.AuditDao
import com.example.trackme.data.local.entity.AuditEventEntity
import com.example.trackme.domain.model.AuditEvent
import com.example.trackme.domain.repository.AuditRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuditRepositoryImpl @Inject constructor(
    private val auditDao: AuditDao,
    private val hasher: Hasher,
    private val timeProvider: TimeProvider,
    private val json: Json
) : AuditRepository {

    override fun observeRecentEvents(limit: Int): Flow<List<AuditEvent>> {
        return auditDao.observeRecent(limit).map { list -> list.map { it.toDomain() } }
    }

    override suspend fun appendEvent(type: String, summary: String, metadata: Map<String, String>) {
        val metadataJson = json.encodeToString(metadata.toSortedMap())
        val previous = auditDao.latestOrNull()
        val createdAt = timeProvider.nowEpochMillis()

        val eventHash = hasher.sha256(
            listOf(previous?.eventHash.orEmpty(), type, summary, metadataJson, createdAt.toString())
                .joinToString(separator = "|")
        )

        auditDao.insert(
            AuditEventEntity(
                type = type,
                summary = summary,
                metadataJson = metadataJson,
                createdAtEpochMs = createdAt,
                previousHash = previous?.eventHash,
                eventHash = eventHash
            )
        )
    }

    private fun AuditEventEntity.toDomain(): AuditEvent {
        return AuditEvent(
            id = id,
            type = type,
            summary = summary,
            metadataJson = metadataJson,
            createdAtEpochMs = createdAtEpochMs,
            previousHash = previousHash,
            eventHash = eventHash
        )
    }
}

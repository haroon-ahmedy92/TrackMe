package com.example.trackme.data.repository

import com.example.trackme.data.local.dao.IncidentDao
import com.example.trackme.data.local.entity.IncidentAttachmentReferenceEntity
import com.example.trackme.data.local.entity.IncidentEvidenceExportEntity
import com.example.trackme.data.local.entity.IncidentNoteEntity
import com.example.trackme.data.local.entity.IncidentStateEntity
import com.example.trackme.data.local.entity.IncidentTimelineEntity
import com.example.trackme.domain.model.IncidentAttachmentReference
import com.example.trackme.domain.model.IncidentCaseNote
import com.example.trackme.domain.model.IncidentEvidenceExport
import com.example.trackme.domain.model.IncidentEvidenceExportFormat
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

    override fun observeNotes(incidentId: String, limit: Int): Flow<List<IncidentCaseNote>> {
        return incidentDao.observeNotes(incidentId, limit).map { rows -> rows.map { it.toDomain() } }
    }

    override fun observeAttachmentReferences(
        incidentId: String,
        limit: Int,
    ): Flow<List<IncidentAttachmentReference>> {
        return incidentDao.observeAttachmentReferences(incidentId, limit).map { rows -> rows.map { it.toDomain() } }
    }

    override fun observeEvidenceExports(incidentId: String, limit: Int): Flow<List<IncidentEvidenceExport>> {
        return incidentDao.observeEvidenceExports(incidentId, limit).map { rows -> rows.map { it.toDomain() } }
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

    override suspend fun appendNote(note: IncidentCaseNote) {
        incidentDao.insertNote(
            IncidentNoteEntity(
                id = note.id,
                incidentId = note.incidentId,
                authorLabel = note.authorLabel,
                body = note.body,
                isPinned = note.isPinned,
                createdAtEpochMs = note.createdAtEpochMs,
                updatedAtEpochMs = note.updatedAtEpochMs
            )
        )
    }

    override suspend fun appendAttachmentReference(attachment: IncidentAttachmentReference) {
        incidentDao.insertAttachmentReference(
            IncidentAttachmentReferenceEntity(
                id = attachment.id,
                incidentId = attachment.incidentId,
                fileName = attachment.fileName,
                description = attachment.description,
                mediaType = attachment.mediaType,
                byteSize = attachment.byteSize,
                addedByLabel = attachment.addedByLabel,
                createdAtEpochMs = attachment.createdAtEpochMs
            )
        )
    }

    override suspend fun appendEvidenceExport(export: IncidentEvidenceExport) {
        incidentDao.insertEvidenceExport(
            IncidentEvidenceExportEntity(
                id = export.id,
                incidentId = export.incidentId,
                format = export.format.name,
                reason = export.reason,
                requestedByLabel = export.requestedByLabel,
                redactionSummary = export.redactionSummary,
                createdAtEpochMs = export.createdAtEpochMs
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

    private fun IncidentNoteEntity.toDomain(): IncidentCaseNote {
        return IncidentCaseNote(
            id = id,
            incidentId = incidentId,
            authorLabel = authorLabel,
            body = body,
            isPinned = isPinned,
            createdAtEpochMs = createdAtEpochMs,
            updatedAtEpochMs = updatedAtEpochMs
        )
    }

    private fun IncidentAttachmentReferenceEntity.toDomain(): IncidentAttachmentReference {
        return IncidentAttachmentReference(
            id = id,
            incidentId = incidentId,
            fileName = fileName,
            description = description,
            mediaType = mediaType,
            byteSize = byteSize,
            addedByLabel = addedByLabel,
            createdAtEpochMs = createdAtEpochMs
        )
    }

    private fun IncidentEvidenceExportEntity.toDomain(): IncidentEvidenceExport {
        return IncidentEvidenceExport(
            id = id,
            incidentId = incidentId,
            format = runCatching { IncidentEvidenceExportFormat.valueOf(format) }
                .getOrDefault(IncidentEvidenceExportFormat.JSON),
            reason = reason,
            requestedByLabel = requestedByLabel,
            redactionSummary = redactionSummary,
            createdAtEpochMs = createdAtEpochMs
        )
    }
}

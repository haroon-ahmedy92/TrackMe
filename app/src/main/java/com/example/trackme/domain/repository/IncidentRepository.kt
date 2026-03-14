package com.example.trackme.domain.repository

import com.example.trackme.domain.model.IncidentAttachmentReference
import com.example.trackme.domain.model.IncidentCaseNote
import com.example.trackme.domain.model.IncidentEvidenceExport
import com.example.trackme.domain.model.IncidentRecord
import com.example.trackme.domain.model.IncidentTimelineEntry
import kotlinx.coroutines.flow.Flow

interface IncidentRepository {
    fun observeCurrentIncident(): Flow<IncidentRecord>
    fun observeTimeline(limit: Int = 200): Flow<List<IncidentTimelineEntry>>
    fun observeNotes(incidentId: String, limit: Int = 100): Flow<List<IncidentCaseNote>>
    fun observeAttachmentReferences(incidentId: String, limit: Int = 50): Flow<List<IncidentAttachmentReference>>
    fun observeEvidenceExports(incidentId: String, limit: Int = 20): Flow<List<IncidentEvidenceExport>>
    suspend fun getCurrentIncident(): IncidentRecord
    suspend fun upsertCurrentIncident(record: IncidentRecord)
    suspend fun appendTimelineEntry(entry: IncidentTimelineEntry)
    suspend fun appendNote(note: IncidentCaseNote)
    suspend fun appendAttachmentReference(attachment: IncidentAttachmentReference)
    suspend fun appendEvidenceExport(export: IncidentEvidenceExport)
}

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
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class IncidentRepositoryImplTest {

    @Test
    fun observeCaseEvidenceMapsNotesAttachmentsAndExports() = runTest {
        val dao = FakeIncidentDao()
        val repository = IncidentRepositoryImpl(dao)

        repository.appendNote(
            IncidentCaseNote(
                id = 0,
                incidentId = "inc-100",
                authorLabel = "Analyst",
                body = "Last seen near depot",
                isPinned = true,
                createdAtEpochMs = 10L,
                updatedAtEpochMs = 20L,
            )
        )
        repository.appendAttachmentReference(
            IncidentAttachmentReference(
                id = 0,
                incidentId = "inc-100",
                fileName = "handover-form.pdf",
                description = "Signed paper form",
                mediaType = "application/pdf",
                byteSize = 1204L,
                addedByLabel = "Analyst",
                createdAtEpochMs = 30L,
            )
        )
        repository.appendEvidenceExport(
            IncidentEvidenceExport(
                id = 0,
                incidentId = "inc-100",
                format = IncidentEvidenceExportFormat.JSON,
                reason = "Case handoff",
                requestedByLabel = "Analyst",
                redactionSummary = "Redact latitude, longitude",
                createdAtEpochMs = 40L,
            )
        )

        val notes = repository.observeNotes("inc-100").first()
        val attachments = repository.observeAttachmentReferences("inc-100").first()
        val exports = repository.observeEvidenceExports("inc-100").first()

        assertEquals(1, notes.size)
        assertEquals("Last seen near depot", notes.first().body)
        assertEquals(1, attachments.size)
        assertEquals("handover-form.pdf", attachments.first().fileName)
        assertEquals(1, exports.size)
        assertEquals(IncidentEvidenceExportFormat.JSON, exports.first().format)
    }
}

private class FakeIncidentDao : IncidentDao {
    private val currentState = MutableStateFlow<IncidentStateEntity?>(null)
    private val timelineState = MutableStateFlow<List<IncidentTimelineEntity>>(emptyList())
    private val notesState = MutableStateFlow<List<IncidentNoteEntity>>(emptyList())
    private val attachmentsState = MutableStateFlow<List<IncidentAttachmentReferenceEntity>>(emptyList())
    private val exportsState = MutableStateFlow<List<IncidentEvidenceExportEntity>>(emptyList())
    private var nextNoteId = 1L
    private var nextAttachmentId = 1L
    private var nextExportId = 1L

    override fun observeCurrent(id: Int): Flow<IncidentStateEntity?> = currentState

    override suspend fun getCurrent(id: Int): IncidentStateEntity? = currentState.value

    override suspend fun upsertCurrent(entity: IncidentStateEntity) {
        currentState.value = entity
    }

    override suspend fun insertTimeline(entity: IncidentTimelineEntity) {
        timelineState.value = listOf(entity.copy(id = timelineState.value.size.toLong() + 1)) + timelineState.value
    }

    override fun observeTimeline(limit: Int): Flow<List<IncidentTimelineEntity>> = timelineState

    override suspend fun insertNote(entity: IncidentNoteEntity) {
        notesState.value = listOf(entity.copy(id = nextNoteId++)) + notesState.value
    }

    override fun observeNotes(incidentId: String, limit: Int): Flow<List<IncidentNoteEntity>> {
        return MutableStateFlow(notesState.value.filter { it.incidentId == incidentId }.take(limit))
    }

    override suspend fun insertAttachmentReference(entity: IncidentAttachmentReferenceEntity) {
        attachmentsState.value = listOf(entity.copy(id = nextAttachmentId++)) + attachmentsState.value
    }

    override fun observeAttachmentReferences(
        incidentId: String,
        limit: Int,
    ): Flow<List<IncidentAttachmentReferenceEntity>> {
        return MutableStateFlow(attachmentsState.value.filter { it.incidentId == incidentId }.take(limit))
    }

    override suspend fun insertEvidenceExport(entity: IncidentEvidenceExportEntity) {
        exportsState.value = listOf(entity.copy(id = nextExportId++)) + exportsState.value
    }

    override fun observeEvidenceExports(
        incidentId: String,
        limit: Int,
    ): Flow<List<IncidentEvidenceExportEntity>> {
        return MutableStateFlow(exportsState.value.filter { it.incidentId == incidentId }.take(limit))
    }
}

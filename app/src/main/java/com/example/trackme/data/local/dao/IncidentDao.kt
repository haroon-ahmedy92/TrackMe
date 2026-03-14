package com.example.trackme.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.trackme.data.local.entity.IncidentAttachmentReferenceEntity
import com.example.trackme.data.local.entity.IncidentEvidenceExportEntity
import com.example.trackme.data.local.entity.IncidentNoteEntity
import com.example.trackme.data.local.entity.IncidentStateEntity
import com.example.trackme.data.local.entity.IncidentTimelineEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface IncidentDao {
    @Query("SELECT * FROM incident_state WHERE id = :id")
    fun observeCurrent(id: Int = IncidentStateEntity.SINGLETON_ID): Flow<IncidentStateEntity?>

    @Query("SELECT * FROM incident_state WHERE id = :id")
    suspend fun getCurrent(id: Int = IncidentStateEntity.SINGLETON_ID): IncidentStateEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertCurrent(entity: IncidentStateEntity)

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertTimeline(entity: IncidentTimelineEntity)

    @Query("SELECT * FROM incident_timeline ORDER BY id DESC LIMIT :limit")
    fun observeTimeline(limit: Int): Flow<List<IncidentTimelineEntity>>

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertNote(entity: IncidentNoteEntity)

    @Query("SELECT * FROM incident_notes WHERE incidentId = :incidentId ORDER BY isPinned DESC, updatedAtEpochMs DESC LIMIT :limit")
    fun observeNotes(incidentId: String, limit: Int): Flow<List<IncidentNoteEntity>>

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertAttachmentReference(entity: IncidentAttachmentReferenceEntity)

    @Query("SELECT * FROM incident_attachment_references WHERE incidentId = :incidentId ORDER BY createdAtEpochMs DESC LIMIT :limit")
    fun observeAttachmentReferences(incidentId: String, limit: Int): Flow<List<IncidentAttachmentReferenceEntity>>

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertEvidenceExport(entity: IncidentEvidenceExportEntity)

    @Query("SELECT * FROM incident_evidence_exports WHERE incidentId = :incidentId ORDER BY createdAtEpochMs DESC LIMIT :limit")
    fun observeEvidenceExports(incidentId: String, limit: Int): Flow<List<IncidentEvidenceExportEntity>>
}

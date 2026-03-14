package com.example.trackme.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.example.trackme.data.local.dao.AuditDao
import com.example.trackme.data.local.dao.DeviceCommandDao
import com.example.trackme.data.local.dao.DeviceStateDao
import com.example.trackme.data.local.dao.EnrollmentDao
import com.example.trackme.data.local.dao.IncidentDao
import com.example.trackme.data.local.dao.LocationDao
import com.example.trackme.data.local.dao.TelemetryQueueDao
import com.example.trackme.data.local.entity.AuditEventEntity
import com.example.trackme.data.local.entity.DeviceCommandEntity
import com.example.trackme.data.local.entity.DeviceStateEntity
import com.example.trackme.data.local.entity.EnrollmentEntity
import com.example.trackme.data.local.entity.IncidentAttachmentReferenceEntity
import com.example.trackme.data.local.entity.IncidentEvidenceExportEntity
import com.example.trackme.data.local.entity.IncidentNoteEntity
import com.example.trackme.data.local.entity.IncidentStateEntity
import com.example.trackme.data.local.entity.IncidentTimelineEntity
import com.example.trackme.data.local.entity.LocationSampleEntity
import com.example.trackme.data.local.entity.TelemetryQueueEntity

@Database(
    entities = [
        EnrollmentEntity::class,
        DeviceStateEntity::class,
        DeviceCommandEntity::class,
        LocationSampleEntity::class,
        AuditEventEntity::class,
        IncidentStateEntity::class,
        IncidentTimelineEntity::class,
        IncidentNoteEntity::class,
        IncidentAttachmentReferenceEntity::class,
        IncidentEvidenceExportEntity::class,
        TelemetryQueueEntity::class
    ],
    version = 8,
    exportSchema = false
)
abstract class TrackMeDatabase : RoomDatabase() {
    abstract fun enrollmentDao(): EnrollmentDao
    abstract fun deviceStateDao(): DeviceStateDao
    abstract fun deviceCommandDao(): DeviceCommandDao
    abstract fun locationDao(): LocationDao
    abstract fun telemetryQueueDao(): TelemetryQueueDao
    abstract fun auditDao(): AuditDao
    abstract fun incidentDao(): IncidentDao
}

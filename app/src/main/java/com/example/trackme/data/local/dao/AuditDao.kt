package com.example.trackme.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.trackme.data.local.entity.AuditEventEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface AuditDao {
    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insert(entity: AuditEventEntity)

    @Query("SELECT * FROM audit_events ORDER BY id DESC LIMIT :limit")
    fun observeRecent(limit: Int): Flow<List<AuditEventEntity>>

    @Query("SELECT * FROM audit_events ORDER BY id DESC LIMIT 1")
    suspend fun latestOrNull(): AuditEventEntity?
}

package com.example.trackme.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.trackme.data.local.entity.DeviceCommandEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface DeviceCommandDao {
    @Query("SELECT * FROM device_commands ORDER BY requestedAtEpochMs DESC")
    fun observeAll(): Flow<List<DeviceCommandEntity>>

    @Query("SELECT * FROM device_commands WHERE status IN (:statuses) ORDER BY requestedAtEpochMs ASC")
    suspend fun getByStatuses(statuses: List<String>): List<DeviceCommandEntity>

    @Query("SELECT * FROM device_commands WHERE status IN (:statuses) AND isServerAcknowledged = 0 ORDER BY requestedAtEpochMs ASC")
    suspend fun getPendingAcknowledgements(statuses: List<String>): List<DeviceCommandEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(rows: List<DeviceCommandEntity>)

    @Query("UPDATE device_commands SET status = :status, lastError = :lastError, deliveredAtEpochMs = COALESCE(deliveredAtEpochMs, :deliveredAtEpochMs), executedAtEpochMs = COALESCE(:executedAtEpochMs, executedAtEpochMs) WHERE commandId = :commandId")
    suspend fun updateStatus(
        commandId: String,
        status: String,
        lastError: String?,
        deliveredAtEpochMs: Long?,
        executedAtEpochMs: Long?
    )

    @Query("UPDATE device_commands SET isServerAcknowledged = :isServerAcknowledged WHERE commandId = :commandId")
    suspend fun updateServerAcknowledged(commandId: String, isServerAcknowledged: Boolean)
}

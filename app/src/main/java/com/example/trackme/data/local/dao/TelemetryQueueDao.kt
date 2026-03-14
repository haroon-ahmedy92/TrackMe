package com.example.trackme.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.trackme.data.local.entity.TelemetryQueueEntity

@Dao
interface TelemetryQueueDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(entity: TelemetryQueueEntity): Long

    @Query(
        """
        SELECT * FROM telemetry_queue
        WHERE uploaded_at_epoch_ms IS NULL AND next_retry_at_epoch_ms <= :nowEpochMs
        ORDER BY created_at_epoch_ms ASC
        LIMIT :limit
        """
    )
    suspend fun getDue(limit: Int, nowEpochMs: Long): List<TelemetryQueueEntity>

    @Query(
        """
        UPDATE telemetry_queue
        SET uploaded_at_epoch_ms = :uploadedAtEpochMs,
            last_attempt_at_epoch_ms = :uploadedAtEpochMs,
            last_error = NULL
        WHERE idempotency_key = :idempotencyKey
        """
    )
    suspend fun markUploaded(idempotencyKey: String, uploadedAtEpochMs: Long)

    @Query(
        """
        UPDATE telemetry_queue
        SET attempt_count = :attemptCount,
            next_retry_at_epoch_ms = :nextRetryAtEpochMs,
            last_attempt_at_epoch_ms = :lastAttemptAtEpochMs,
            last_error = :lastError
        WHERE idempotency_key = :idempotencyKey
        """
    )
    suspend fun markRetry(
        idempotencyKey: String,
        attemptCount: Int,
        nextRetryAtEpochMs: Long,
        lastAttemptAtEpochMs: Long,
        lastError: String,
    )

    @Query("SELECT COUNT(*) FROM telemetry_queue WHERE uploaded_at_epoch_ms IS NULL")
    suspend fun countPending(): Int
}

package com.example.trackme.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.trackme.data.local.entity.LocationSampleEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface LocationDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(entity: LocationSampleEntity)

    @Query("SELECT * FROM location_samples ORDER BY capturedAtEpochMs DESC LIMIT 1")
    fun observeLatest(): Flow<LocationSampleEntity?>

    @Query("SELECT * FROM location_samples ORDER BY capturedAtEpochMs DESC LIMIT :limit")
    fun observeRecent(limit: Int): Flow<List<LocationSampleEntity>>
}

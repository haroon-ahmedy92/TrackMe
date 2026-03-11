package com.example.trackme.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.trackme.data.local.entity.DeviceStateEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface DeviceStateDao {
    @Query("SELECT * FROM device_state WHERE id = :id")
    fun observeById(id: Int = DeviceStateEntity.SINGLETON_ID): Flow<DeviceStateEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entity: DeviceStateEntity)
}

package com.example.trackme.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.trackme.data.local.entity.EnrollmentEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface EnrollmentDao {
    @Query("SELECT * FROM enrollment WHERE id = :id")
    fun observeById(id: Int = EnrollmentEntity.SINGLETON_ID): Flow<EnrollmentEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entity: EnrollmentEntity)
}

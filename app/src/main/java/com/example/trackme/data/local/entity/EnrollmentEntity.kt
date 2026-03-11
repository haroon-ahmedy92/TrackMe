package com.example.trackme.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "enrollment")
data class EnrollmentEntity(
    @PrimaryKey val id: Int = SINGLETON_ID,
    val isEnrolled: Boolean,
    val organizationName: String?,
    val consentVersion: String?,
    val enrolledAtEpochMs: Long?
) {
    companion object {
        const val SINGLETON_ID = 1
    }
}

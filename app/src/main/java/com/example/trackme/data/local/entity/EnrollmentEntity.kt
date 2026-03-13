package com.example.trackme.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "enrollment")
data class EnrollmentEntity(
    @PrimaryKey val id: Int = SINGLETON_ID,
    val isEnrolled: Boolean,
    val organizationName: String?,
    val consentVersion: String?,
    val enrolledAtEpochMs: Long?,
    val deviceAlias: String?,
    val orgId: String?,
    val deviceId: String?,
    val ownershipBindingId: String?,
    val ownerSubject: String?,
    val ownershipType: String?,
    val authorizationRole: String?,
    val pairingMethod: String?,
    val keyId: String?,
    val keyAlgorithm: String?,
    val registrationState: String?
) {
    companion object {
        const val SINGLETON_ID = 1
    }
}

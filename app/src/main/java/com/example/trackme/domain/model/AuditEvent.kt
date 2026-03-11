package com.example.trackme.domain.model

data class AuditEvent(
    val id: Long,
    val type: String,
    val summary: String,
    val metadataJson: String,
    val createdAtEpochMs: Long,
    val previousHash: String?,
    val eventHash: String
)

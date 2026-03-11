package com.example.trackme.ui.audit

import com.example.trackme.domain.model.AuditEvent

data class AuditLogUiState(
    val events: List<AuditEvent> = emptyList()
)

package com.example.trackme.feature.audit

import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.model.AuditEvent

typealias AuditUiState = AsyncUiState<List<AuditEvent>>

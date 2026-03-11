package com.example.trackme.ui.audit

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.domain.usecase.ObserveAuditLogUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AuditLogViewModel @Inject constructor(
    observeAuditLogUseCase: ObserveAuditLogUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuditLogUiState())
    val uiState: StateFlow<AuditLogUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            observeAuditLogUseCase().collect { events ->
                _uiState.update { it.copy(events = events) }
            }
        }
    }
}

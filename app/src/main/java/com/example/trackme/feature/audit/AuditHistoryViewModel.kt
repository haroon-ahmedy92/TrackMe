package com.example.trackme.feature.audit

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.usecase.ObserveAuditLogUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

@HiltViewModel
class AuditHistoryViewModel @Inject constructor(
    private val observeAuditLogUseCase: ObserveAuditLogUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow<AuditUiState>(AsyncUiState.Loading)
    val uiState: StateFlow<AuditUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            observeAuditLogUseCase().collect { logs ->
                _uiState.value = AsyncUiState.Data(logs)
            }
        }
    }
}

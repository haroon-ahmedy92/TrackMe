package com.example.trackme.feature.enrollment

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.usecase.EnrollDeviceUseCase
import com.example.trackme.domain.usecase.GetEnrollmentDisclosureUseCase
import com.example.trackme.worker.CheckInScheduler
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

@HiltViewModel
class EnrollmentViewModel @Inject constructor(
    private val enrollDeviceUseCase: EnrollDeviceUseCase,
    private val getEnrollmentDisclosureUseCase: GetEnrollmentDisclosureUseCase,
    private val checkInScheduler: CheckInScheduler
) : ViewModel() {

    private val _uiState = MutableStateFlow<EnrollmentUiState>(AsyncUiState.Data(EnrollmentForm()))
    val uiState: StateFlow<EnrollmentUiState> = _uiState.asStateFlow()

    val disclosure = getEnrollmentDisclosureUseCase()

    fun onOrganizationNameChanged(value: String) {
        update { it.copy(organizationName = value) }
    }

    fun onAuthorizationConfirmed(checked: Boolean) {
        update { it.copy(authorizationConfirmed = checked) }
    }

    fun enroll(onSuccess: () -> Unit) {
        val data = (_uiState.value as? AsyncUiState.Data)?.value ?: return
        if (data.organizationName.isBlank() || !data.authorizationConfirmed) {
            update { it.copy(errorMessage = "Please provide organization name and authorization confirmation.") }
            return
        }

        viewModelScope.launch {
            update { it.copy(isSubmitting = true, errorMessage = null) }
            runCatching {
                enrollDeviceUseCase(
                    organizationName = data.organizationName.trim(),
                    consentVersion = disclosure.version
                )
                checkInScheduler.scheduleNormalCheckIn()
            }.onSuccess {
                onSuccess()
            }.onFailure {
                update { form ->
                    form.copy(
                        isSubmitting = false,
                        errorMessage = it.message ?: "Enrollment failed"
                    )
                }
            }
        }
    }

    private fun update(transform: (EnrollmentForm) -> EnrollmentForm) {
        val state = _uiState.value
        if (state is AsyncUiState.Data) {
            _uiState.update { AsyncUiState.Data(transform(state.value)) }
        }
    }
}

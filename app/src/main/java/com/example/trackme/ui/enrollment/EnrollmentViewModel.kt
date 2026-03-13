package com.example.trackme.ui.enrollment

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.domain.model.EnrollmentAuthorizationRole
import com.example.trackme.domain.model.EnrollmentRequest
import com.example.trackme.domain.model.OwnershipType
import com.example.trackme.domain.model.PairingMethod
import com.example.trackme.domain.repository.EnrollmentRepository
import com.example.trackme.domain.usecase.EnrollDeviceUseCase
import com.example.trackme.domain.usecase.GetEnrollmentDisclosureUseCase
import com.example.trackme.worker.CheckInScheduler
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class EnrollmentViewModel @Inject constructor(
    private val getEnrollmentDisclosureUseCase: GetEnrollmentDisclosureUseCase,
    private val enrollDeviceUseCase: EnrollDeviceUseCase,
    private val enrollmentRepository: EnrollmentRepository,
    private val checkInScheduler: CheckInScheduler
) : ViewModel() {

    private val _uiState = MutableStateFlow(
        EnrollmentUiState(disclosure = getEnrollmentDisclosureUseCase())
    )
    val uiState: StateFlow<EnrollmentUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            enrollmentRepository.observeEnrollmentStatus().collect { status ->
                _uiState.update { it.copy(isEnrolled = status.isEnrolled) }
            }
        }
    }

    fun onOrganizationNameChanged(value: String) {
        _uiState.update { it.copy(organizationName = value) }
    }

    fun onConsentChecked(checked: Boolean) {
        _uiState.update { it.copy(consentAccepted = checked) }
    }

    fun enroll() {
        val state = _uiState.value
        if (!state.consentAccepted || state.organizationName.isBlank() || state.disclosure == null) {
            _uiState.update {
                it.copy(errorMessage = "Organization name and explicit consent are required.")
            }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(isSubmitting = true, errorMessage = null) }
            runCatching {
                enrollDeviceUseCase(
                    EnrollmentRequest(
                        organizationName = state.organizationName.trim(),
                        consentVersion = state.disclosure.version,
                        deviceAlias = "Legacy Enrollment Device",
                        ownerSubject = null,
                        ownershipType = OwnershipType.ORGANIZATION_OWNED,
                        authorizationRole = EnrollmentAuthorizationRole.ADMIN,
                        pairingCredential = "legacy-local-enrollment",
                        pairingMethod = PairingMethod.ENROLLMENT_TOKEN
                    )
                )
                checkInScheduler.scheduleNormalCheckIn()
            }.onFailure {
                _uiState.update { current ->
                    current.copy(
                        isSubmitting = false,
                        errorMessage = it.message ?: "Enrollment failed."
                    )
                }
            }.onSuccess {
                _uiState.update { current ->
                    current.copy(isSubmitting = false)
                }
            }
        }
    }
}

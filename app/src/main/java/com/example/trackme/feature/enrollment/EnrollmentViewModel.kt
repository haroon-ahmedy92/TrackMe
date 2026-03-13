package com.example.trackme.feature.enrollment

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.model.EnrollmentAuthorizationRole
import com.example.trackme.domain.model.EnrollmentRequest
import com.example.trackme.domain.model.OwnershipType
import com.example.trackme.domain.model.PairingMethod
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
    private val enrollmentCoordinator: EnrollmentCoordinator,
    private val checkInScheduler: CheckInScheduler
) : ViewModel() {

    private val _uiState = MutableStateFlow<EnrollmentUiState>(AsyncUiState.Data(EnrollmentForm()))
    val uiState: StateFlow<EnrollmentUiState> = _uiState.asStateFlow()

    val disclosure = enrollmentCoordinator.disclosure()

    fun onOrganizationNameChanged(value: String) = update { it.copy(organizationName = value) }

    fun onDeviceAliasChanged(value: String) = update { it.copy(deviceAlias = value) }

    fun onOwnerSubjectChanged(value: String) = update { it.copy(ownerSubject = value) }

    fun onPairingCredentialChanged(value: String) = update { it.copy(pairingCredential = value) }

    fun onOwnershipTypeChanged(value: OwnershipType) {
        update {
            it.copy(
                ownershipType = value,
                ownerSubject = if (value == OwnershipType.ORGANIZATION_OWNED) "" else it.ownerSubject
            )
        }
    }

    fun onAuthorizationRoleChanged(value: EnrollmentAuthorizationRole) = update { it.copy(authorizationRole = value) }

    fun onPairingMethodChanged(value: PairingMethod) = update { it.copy(pairingMethod = value) }

    fun onAuthorizationConfirmed(checked: Boolean) = update { it.copy(authorizationConfirmed = checked) }

    fun enroll(onSuccess: () -> Unit) {
        val form = (_uiState.value as? AsyncUiState.Data)?.value ?: return
        val errorMessage = validate(form)
        if (errorMessage != null) {
            update { it.copy(errorMessage = errorMessage) }
            return
        }

        viewModelScope.launch {
            update { it.copy(isSubmitting = true, errorMessage = null) }
            runCatching {
                enrollmentCoordinator.enroll(
                    EnrollmentRequest(
                        organizationName = form.organizationName.trim(),
                        consentVersion = disclosure.version,
                        deviceAlias = form.deviceAlias.trim(),
                        ownerSubject = form.ownerSubject.trim().ifBlank { null },
                        ownershipType = form.ownershipType,
                        authorizationRole = form.authorizationRole,
                        pairingCredential = form.pairingCredential.trim(),
                        pairingMethod = form.pairingMethod
                    )
                )
                checkInScheduler.scheduleNormalCheckIn()
            }.onSuccess {
                update { it.copy(isSubmitting = false, errorMessage = null) }
                onSuccess()
            }.onFailure { throwable ->
                update {
                    it.copy(
                        isSubmitting = false,
                        errorMessage = throwable.message ?: "Enrollment failed"
                    )
                }
            }
        }
    }

    private fun validate(form: EnrollmentForm): String? {
        if (form.organizationName.isBlank()) return "Organization name is required."
        if (form.deviceAlias.isBlank()) return "Device alias is required so operators can identify this phone."
        if (form.pairingCredential.isBlank()) return "Paste the enrollment token or QR pairing link from the admin console."
        if (form.ownershipType == OwnershipType.SINGLE_USER && form.ownerSubject.isBlank()) {
            return "Owner subject is required for a single-user owned device."
        }
        if (!form.authorizationConfirmed) {
            return "You must confirm you are the owner or an authorized administrator."
        }
        return null
    }

    private fun update(transform: (EnrollmentForm) -> EnrollmentForm) {
        val state = _uiState.value
        if (state is AsyncUiState.Data) {
            _uiState.update { AsyncUiState.Data(transform(state.value)) }
        }
    }
}

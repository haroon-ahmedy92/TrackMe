package com.example.trackme.feature.enrollment

import com.example.trackme.compliance.ConsentDisclosure
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.model.EnrollmentAuthorizationRole
import com.example.trackme.domain.model.EnrollmentRequest
import com.example.trackme.domain.model.EnrollmentStatus
import com.example.trackme.domain.model.OwnershipType
import com.example.trackme.domain.model.PairingMethod
import com.example.trackme.domain.model.RegistrationState
import com.example.trackme.testing.MainDispatcherRule
import com.example.trackme.worker.CheckInScheduler
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class EnrollmentViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    @Test
    fun enroll_requires_owner_subject_for_single_user_ownership() = runTest {
        val viewModel = EnrollmentViewModel(
            enrollmentCoordinator = FakeEnrollmentCoordinator(),
            checkInScheduler = FakeCheckInScheduler()
        )
        viewModel.onOrganizationNameChanged("Acme")
        viewModel.onDeviceAliasChanged("Phone 01")
        viewModel.onPairingCredentialChanged("token-123")
        viewModel.onOwnershipTypeChanged(OwnershipType.SINGLE_USER)
        viewModel.onAuthorizationConfirmed(true)

        viewModel.enroll(onSuccess = {})
        advanceUntilIdle()

        val state = (viewModel.uiState.value as AsyncUiState.Data).value
        assertEquals(
            "Owner subject is required for a single-user owned device.",
            state.errorMessage
        )
    }

    @Test
    fun enroll_submits_request_and_schedules_checkins() = runTest {
        val coordinator = FakeEnrollmentCoordinator()
        val scheduler = FakeCheckInScheduler()
        var successCalled = false
        val viewModel = EnrollmentViewModel(
            enrollmentCoordinator = coordinator,
            checkInScheduler = scheduler
        )
        viewModel.onOrganizationNameChanged("Acme")
        viewModel.onDeviceAliasChanged("Phone 01")
        viewModel.onPairingCredentialChanged("trackme://pair?token=abc")
        viewModel.onOwnershipTypeChanged(OwnershipType.ORGANIZATION_OWNED)
        viewModel.onAuthorizationRoleChanged(EnrollmentAuthorizationRole.ADMIN)
        viewModel.onPairingMethodChanged(PairingMethod.QR_CODE_URI)
        viewModel.onAuthorizationConfirmed(true)

        viewModel.enroll(onSuccess = { successCalled = true })
        advanceUntilIdle()

        assertTrue(successCalled)
        assertTrue(scheduler.normalScheduled)
        assertEquals(PairingMethod.QR_CODE_URI, coordinator.lastRequest?.pairingMethod)
        assertEquals(OwnershipType.ORGANIZATION_OWNED, coordinator.lastRequest?.ownershipType)
        val state = (viewModel.uiState.value as AsyncUiState.Data).value
        assertFalse(state.isSubmitting)
    }
}

private class FakeEnrollmentCoordinator : EnrollmentCoordinator {
    var lastRequest: EnrollmentRequest? = null

    override fun disclosure(): ConsentDisclosure {
        return ConsentDisclosure(
            version = "2026-03-10",
            title = "Enrollment Disclosure",
            bulletPoints = listOf("Visible enrollment only")
        )
    }

    override suspend fun enroll(request: EnrollmentRequest): EnrollmentStatus {
        lastRequest = request
        return EnrollmentStatus(
            isEnrolled = true,
            organizationName = request.organizationName,
            consentVersion = request.consentVersion,
            enrolledAtEpochMs = 1L,
            deviceAlias = request.deviceAlias,
            ownerSubject = request.ownerSubject,
            ownershipType = request.ownershipType,
            authorizationRole = request.authorizationRole,
            pairingMethod = request.pairingMethod,
            registrationState = RegistrationState.VERIFIED
        )
    }
}

private class FakeCheckInScheduler : CheckInScheduler {
    var normalScheduled = false

    override suspend fun scheduleNormalCheckIn() {
        normalScheduled = true
    }

    override suspend fun scheduleMisplacedCheckIn() = Unit

    override suspend fun scheduleLostModeCheckIn(untilEpochMs: Long) = Unit

    override suspend fun cancelMisplacedCheckIn() = Unit

    override suspend fun cancelLostModeCheckIn() = Unit
}

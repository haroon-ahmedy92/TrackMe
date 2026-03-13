package com.example.trackme.feature.enrollment

import com.example.trackme.compliance.ConsentDisclosure
import com.example.trackme.domain.model.EnrollmentRequest
import com.example.trackme.domain.model.EnrollmentStatus
import com.example.trackme.domain.usecase.EnrollDeviceUseCase
import com.example.trackme.domain.usecase.GetEnrollmentDisclosureUseCase
import javax.inject.Inject

interface EnrollmentCoordinator {
    fun disclosure(): ConsentDisclosure
    suspend fun enroll(request: EnrollmentRequest): EnrollmentStatus
}

class DefaultEnrollmentCoordinator @Inject constructor(
    private val enrollDeviceUseCase: EnrollDeviceUseCase,
    private val getEnrollmentDisclosureUseCase: GetEnrollmentDisclosureUseCase
) : EnrollmentCoordinator {
    override fun disclosure(): ConsentDisclosure = getEnrollmentDisclosureUseCase()

    override suspend fun enroll(request: EnrollmentRequest): EnrollmentStatus = enrollDeviceUseCase(request)
}

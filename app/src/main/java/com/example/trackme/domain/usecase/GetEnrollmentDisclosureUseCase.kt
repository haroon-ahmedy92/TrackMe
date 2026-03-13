package com.example.trackme.domain.usecase

import com.example.trackme.compliance.ConsentDisclosure
import com.example.trackme.domain.repository.PolicyRepository
import javax.inject.Inject

open class GetEnrollmentDisclosureUseCase @Inject constructor(
    private val policyRepository: PolicyRepository
) {
    open operator fun invoke(): ConsentDisclosure = policyRepository.enrollmentDisclosure()
}

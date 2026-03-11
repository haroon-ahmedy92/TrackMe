package com.example.trackme.data.repository

import com.example.trackme.compliance.CompliancePolicy
import com.example.trackme.compliance.ConsentDisclosure
import com.example.trackme.domain.repository.PolicyRepository
import javax.inject.Inject

class PolicyRepositoryImpl @Inject constructor(
    private val compliancePolicy: CompliancePolicy
) : PolicyRepository {
    override fun enrollmentDisclosure(): ConsentDisclosure = compliancePolicy.enrollmentDisclosure()
}

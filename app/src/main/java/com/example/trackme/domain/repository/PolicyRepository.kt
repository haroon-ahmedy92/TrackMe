package com.example.trackme.domain.repository

import com.example.trackme.compliance.ConsentDisclosure

interface PolicyRepository {
    fun enrollmentDisclosure(): ConsentDisclosure
}

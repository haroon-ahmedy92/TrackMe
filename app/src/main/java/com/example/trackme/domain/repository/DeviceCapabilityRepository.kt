package com.example.trackme.domain.repository

interface DeviceCapabilityRepository {
    fun supportsPolicyManagedRemoteActions(): Boolean
}

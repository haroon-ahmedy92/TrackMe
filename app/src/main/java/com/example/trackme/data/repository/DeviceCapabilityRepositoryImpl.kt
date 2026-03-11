package com.example.trackme.data.repository

import android.app.admin.DevicePolicyManager
import android.content.Context
import com.example.trackme.domain.repository.DeviceCapabilityRepository
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DeviceCapabilityRepositoryImpl @Inject constructor(
    @ApplicationContext private val context: Context
) : DeviceCapabilityRepository {

    override fun supportsPolicyManagedRemoteActions(): Boolean {
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val packageName = context.packageName
        return dpm.isDeviceOwnerApp(packageName) || dpm.isProfileOwnerApp(packageName)
    }
}

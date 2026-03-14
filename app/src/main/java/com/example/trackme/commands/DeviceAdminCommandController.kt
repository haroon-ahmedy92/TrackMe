package com.example.trackme.commands

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import com.example.trackme.domain.repository.DeviceCapabilityRepository
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

interface DeviceAdminCommandController {
    fun lockDevice(): Result<Unit>
    fun wipeDevice(): Result<Unit>
}

@Singleton
class AndroidDeviceAdminCommandController @Inject constructor(
    @ApplicationContext private val context: Context,
    private val deviceCapabilityRepository: DeviceCapabilityRepository,
) : DeviceAdminCommandController {

    override fun lockDevice(): Result<Unit> {
        return runCatching {
            ensurePolicyManagedSupport()
            devicePolicyManager().lockNow()
        }
    }

    override fun wipeDevice(): Result<Unit> {
        return runCatching {
            ensurePolicyManagedSupport()
            devicePolicyManager().wipeData(0)
        }
    }

    private fun ensurePolicyManagedSupport() {
        check(deviceCapabilityRepository.supportsPolicyManagedRemoteActions()) {
            "This device is not policy-managed for lock or wipe commands."
        }
        val adminComponent = adminComponent()
        check(devicePolicyManager().isAdminActive(adminComponent)) {
            "TrackMe device-admin component is not active on this device."
        }
    }

    private fun devicePolicyManager(): DevicePolicyManager {
        return context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
    }

    private fun adminComponent(): ComponentName {
        return ComponentName(context, TrackMeDeviceAdminReceiver::class.java)
    }
}

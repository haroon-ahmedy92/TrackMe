package com.example.trackme.location

import android.content.Context
import android.content.pm.PackageManager
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject

interface WifiRttCapabilityChecker {
    fun isSupported(): Boolean
}

class AndroidWifiRttCapabilityChecker @Inject constructor(
    @ApplicationContext private val context: Context
) : WifiRttCapabilityChecker {
    override fun isSupported(): Boolean {
        return context.packageManager.hasSystemFeature(PackageManager.FEATURE_WIFI_RTT)
    }
}

package com.example.trackme.trust

import android.content.Context
import android.content.pm.ApplicationInfo
import android.os.Build
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
open class AppTrustSignalCollector @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    open fun collect(): AppTrustSignals {
        val applicationDebuggable = (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
        val buildTags = Build.TAGS.orEmpty()
        val suBinaryPresent = COMMON_SU_PATHS.any { path -> File(path).exists() }
        return AppTrustSignals(
            debugBuild = !Build.TYPE.equals("user", ignoreCase = true),
            debuggableApp = applicationDebuggable,
            testKeysBuild = buildTags.contains("test-keys", ignoreCase = true),
            suBinaryPresent = suBinaryPresent,
        )
    }

    private companion object {
        val COMMON_SU_PATHS = listOf(
            "/system/bin/su",
            "/system/xbin/su",
            "/sbin/su",
            "/vendor/bin/su",
        )
    }
}

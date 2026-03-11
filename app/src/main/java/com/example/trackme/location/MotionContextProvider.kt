package com.example.trackme.location

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat
import com.example.trackme.domain.model.MotionState
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject

interface MotionContextProvider {
    fun resolveMotionState(speedMetersPerSecond: Float?): MotionState
}

class DefaultMotionContextProvider @Inject constructor(
    @ApplicationContext private val context: Context
) : MotionContextProvider {

    override fun resolveMotionState(speedMetersPerSecond: Float?): MotionState {
        // TODO: Integrate ActivityRecognitionClient updates when enrollment flow explicitly grants permission.
        // MVP uses speed-derived movement context and returns UNKNOWN when no speed signal exists.
        if (speedMetersPerSecond == null) return MotionState.UNKNOWN
        return when {
            speedMetersPerSecond < 0.8f -> MotionState.STILL
            speedMetersPerSecond < 3.5f -> MotionState.ON_FOOT
            else -> MotionState.IN_VEHICLE
        }
    }

    fun isActivityRecognitionPermissionGranted(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return true
        return ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACTIVITY_RECOGNITION
        ) == PackageManager.PERMISSION_GRANTED
    }
}

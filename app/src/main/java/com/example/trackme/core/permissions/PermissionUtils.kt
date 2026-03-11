package com.example.trackme.core.permissions

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat

object PermissionUtils {

    fun hasForegroundLocation(context: Context): Boolean {
        val fine = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
        val coarse = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION)
        return fine == PackageManager.PERMISSION_GRANTED || coarse == PackageManager.PERMISSION_GRANTED
    }

    fun requiresBackgroundLocationStep(): Boolean = Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q

    fun hasBackgroundLocation(context: Context): Boolean {
        if (!requiresBackgroundLocationStep()) return true
        val background = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_BACKGROUND_LOCATION)
        return background == PackageManager.PERMISSION_GRANTED
    }
}

package com.example.trackme.data.repository

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.example.trackme.R
import com.example.trackme.domain.repository.IncidentNotificationGateway
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class IncidentNotificationGatewayImpl @Inject constructor(
    @ApplicationContext private val context: Context
) : IncidentNotificationGateway {

    override suspend fun notifyEscalation(title: String, body: String): Result<Unit> {
        return runCatching {
            ensureChannel()
            if (!canPostNotification()) {
                throw IllegalStateException("Notification permission not granted.")
            }
            val notification = NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(NotificationCompat.BigTextStyle().bigText(body))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                .build()

            NotificationManagerCompat.from(context)
                .notify(System.currentTimeMillis().toInt(), notification)
        }
    }

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel(
            CHANNEL_ID,
            CHANNEL_NAME,
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Visible incident and recovery escalation notifications."
        }
        manager.createNotificationChannel(channel)
    }

    private fun canPostNotification(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return true
        return ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.POST_NOTIFICATIONS
        ) == PackageManager.PERMISSION_GRANTED
    }

    companion object {
        private const val CHANNEL_ID = "incident_recovery_alerts"
        private const val CHANNEL_NAME = "Incident Recovery Alerts"
    }
}

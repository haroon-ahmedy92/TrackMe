package com.example.trackme.commands

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
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

interface RecoveryMessageNotifier {
    fun showRecoveryMessage(message: String, reason: String): Result<Unit>
    fun showCommandUpdate(title: String, body: String): Result<Unit>
}

@Singleton
class AndroidRecoveryMessageNotifier @Inject constructor(
    @ApplicationContext private val context: Context,
) : RecoveryMessageNotifier {

    override fun showRecoveryMessage(message: String, reason: String): Result<Unit> {
        return showCommandUpdate(
            title = context.getString(R.string.recovery_notification_title),
            body = "$message\n\nReason: $reason",
        )
    }

    override fun showCommandUpdate(title: String, body: String): Result<Unit> {
        return runCatching {
            ensureChannel()
            checkNotificationsAllowed()
            val notification = NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(NotificationCompat.BigTextStyle().bigText(body))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                .build()
            NotificationManagerCompat.from(context).notify(body.hashCode(), notification)
        }
    }

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel(
            CHANNEL_ID,
            context.getString(R.string.recovery_notification_channel_name),
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = context.getString(R.string.recovery_notification_channel_description)
        }
        manager.createNotificationChannel(channel)
    }

    private fun checkNotificationsAllowed() {
        val notificationsEnabled = NotificationManagerCompat.from(context).areNotificationsEnabled()
        check(notificationsEnabled) { "Notifications are disabled for TrackMe." }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
            check(granted) { "POST_NOTIFICATIONS permission has not been granted." }
        }
    }

    companion object {
        const val CHANNEL_ID = "trackme_recovery_commands"
    }
}

package com.example.trackme.messaging

import com.example.trackme.commands.DeviceCommandSyncScheduler
import com.example.trackme.core.AppInfoProvider
import com.example.trackme.domain.repository.CommandRepository
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

@AndroidEntryPoint
class TrackMeFirebaseMessagingService : FirebaseMessagingService() {

    @Inject
    lateinit var commandRepository: CommandRepository

    @Inject
    lateinit var commandSyncScheduler: DeviceCommandSyncScheduler

    @Inject
    lateinit var appInfoProvider: AppInfoProvider

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onNewToken(token: String) {
        serviceScope.launch {
            runCatching {
                commandRepository.registerPushToken(token, appInfoProvider.versionName())
                commandSyncScheduler.scheduleImmediateSync()
            }
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val hasCommandData = message.data.containsKey("remote_action_id") || message.data.containsKey("command_available")
        if (!hasCommandData) return
        serviceScope.launch {
            commandSyncScheduler.scheduleImmediateSync()
        }
    }
}

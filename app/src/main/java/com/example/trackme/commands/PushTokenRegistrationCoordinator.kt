package com.example.trackme.commands

import com.example.trackme.core.AppInfoProvider
import com.example.trackme.domain.repository.CommandRepository
import com.google.firebase.messaging.FirebaseMessaging
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.tasks.await

@Singleton
class PushTokenRegistrationCoordinator @Inject constructor(
    private val commandRepository: CommandRepository,
    private val appInfoProvider: AppInfoProvider,
) {
    suspend fun registerCurrentTokenIfAvailable() {
        val token = runCatching { FirebaseMessaging.getInstance().token.await() }.getOrNull() ?: return
        commandRepository.registerPushToken(token, appInfoProvider.versionName())
    }
}

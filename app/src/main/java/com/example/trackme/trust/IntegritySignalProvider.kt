package com.example.trackme.trust

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf

interface IntegritySignalProvider {
    suspend fun currentSignal(): IntegritySignal
    fun observeSignal(): Flow<IntegritySignal>
}

@Singleton
class PlayIntegritySignalProvider @Inject constructor(
    @ApplicationContext private val context: Context,
) : IntegritySignalProvider {
    override suspend fun currentSignal(): IntegritySignal = buildSignal()

    override fun observeSignal(): Flow<IntegritySignal> = flowOf(buildSignal())

    private fun buildSignal(): IntegritySignal {
        val providerAvailable = isClassAvailable("com.google.android.play.core.integrity.IntegrityManagerFactory")
        return if (providerAvailable) {
            IntegritySignal(
                token = null,
                status = "advisory",
                trusted = false,
                provider = "play_integrity",
                message =
                    "Play Integrity support is present on this device, but server-side verification is not configured for this build. Treat this as advisory only.",
            )
        } else {
            IntegritySignal(
                token = null,
                status = "unavailable",
                trusted = false,
                provider = "play_integrity",
                message =
                    "Play Integrity services are unavailable on this device or not included in this build. Trust status remains limited.",
            )
        }
    }

    private fun isClassAvailable(className: String): Boolean = try {
        Class.forName(className)
        true
    } catch (_: Throwable) {
        false
    }
}

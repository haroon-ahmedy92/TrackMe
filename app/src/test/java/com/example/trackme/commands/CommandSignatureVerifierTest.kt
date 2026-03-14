package com.example.trackme.commands

import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import kotlinx.serialization.json.Json
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CommandSignatureVerifierTest {

    private val verifier = CommandSignatureVerifier(
        json = Json {
            ignoreUnknownKeys = true
            explicitNulls = false
        }
    )

    @Test
    fun verify_accepts_valid_placeholder_signature() {
        val payloadJson = """{"action_kind":"display_recovery_message","recovery_message":"Call +255700000000","requested_at":"2026-03-14T10:00:00Z"}"""
        val signature = sign(payloadJson)

        assertTrue(verifier.verify(payloadJson, signature, CommandSignatureVerifier.SUPPORTED_ALGORITHM))
    }

    @Test
    fun verify_rejects_tampered_payload() {
        val originalPayload = """{"action_kind":"display_recovery_message","recovery_message":"Call +255700000000","requested_at":"2026-03-14T10:00:00Z"}"""
        val tamperedPayload = """{"action_kind":"display_recovery_message","recovery_message":"Ignore owner","requested_at":"2026-03-14T10:00:00Z"}"""
        val signature = sign(originalPayload)

        assertFalse(verifier.verify(tamperedPayload, signature, CommandSignatureVerifier.SUPPORTED_ALGORITHM))
    }

    private fun sign(payloadJson: String): String {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec("trackme-dev-command-secret-change-me".toByteArray(), "HmacSHA256"))
        return mac.doFinal(payloadJson.toByteArray()).joinToString(separator = "") { "%02x".format(it) }
    }
}

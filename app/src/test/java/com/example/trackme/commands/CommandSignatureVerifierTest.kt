package com.example.trackme.commands

import java.security.KeyPairGenerator
import java.security.Signature
import java.util.Base64
import kotlinx.serialization.json.Json
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CommandSignatureVerifierTest {

    private val keyPair = KeyPairGenerator.getInstance("EC").apply {
        initialize(256)
    }.generateKeyPair()

    private val verifier = CommandSignatureVerifier(
        json = Json {
            ignoreUnknownKeys = true
            explicitNulls = false
        },
        configuredPublicKeyPem = keyPair.public.toPem(),
        forTests = true,
    )

    @Test
    fun verify_accepts_valid_backend_signature() {
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
        val signature = Signature.getInstance("SHA256withECDSA").apply {
            initSign(keyPair.private)
            update(payloadJson.encodeToByteArray())
        }.sign()
        return Base64.getEncoder().encodeToString(signature)
    }

    private fun java.security.PublicKey.toPem(): String {
        val base64 = Base64.getEncoder().encodeToString(encoded)
        return buildString {
            appendLine("-----BEGIN PUBLIC KEY-----")
            base64.chunked(64).forEach(::appendLine)
            append("-----END PUBLIC KEY-----")
        }
    }
}

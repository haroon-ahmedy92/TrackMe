package com.example.trackme.commands

import com.example.trackme.BuildConfig
import java.security.KeyFactory
import java.security.PublicKey
import java.security.Signature
import java.security.spec.X509EncodedKeySpec
import java.util.Base64
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

/**
 * Verifies backend command envelopes using the configured server public key.
 *
 * This keeps command authenticity separate from device telemetry signing: the device trusts
 * commands signed by the backend/operator control plane, while the backend trusts telemetry
 * signed by the device key.
 */
@Singleton
class CommandSignatureVerifier private constructor(
    private val json: Json,
    private val configuredPublicKeyPem: String,
) {
    @Inject
    constructor(json: Json) : this(json, BuildConfig.TRACKME_COMMAND_VERIFICATION_PUBLIC_KEY_PEM)

    internal constructor(
        json: Json,
        configuredPublicKeyPem: String,
        forTests: Boolean,
    ) : this(json, configuredPublicKeyPem)

    fun verify(payloadJson: String, signature: String, algorithm: String): Boolean {
        if (algorithm != SUPPORTED_ALGORITHM) return false
        val publicKey = loadConfiguredPublicKey() ?: return false
        val payload = runCatching { json.parseToJsonElement(payloadJson) }.getOrNull() ?: return false
        val canonicalJson = canonicalJson(payload)
        return runCatching {
            Signature.getInstance(JAVA_SIGNATURE_ALGORITHM).apply {
                initVerify(publicKey)
                update(canonicalJson.encodeToByteArray())
            }.verify(Base64.getDecoder().decode(signature))
        }.getOrDefault(false)
    }

    fun hasVerificationMaterial(): Boolean = loadConfiguredPublicKey() != null

    private fun loadConfiguredPublicKey(): PublicKey? {
        val pem = configuredPublicKeyPem.trim()
        if (pem.isBlank()) return null
        val normalized = pem
            .replace("\\n", "\n")
            .replace("-----BEGIN PUBLIC KEY-----", "")
            .replace("-----END PUBLIC KEY-----", "")
            .replace("\\s".toRegex(), "")
        val decoded = runCatching { Base64.getDecoder().decode(normalized) }.getOrNull() ?: return null
        return runCatching {
            KeyFactory.getInstance("EC").generatePublic(X509EncodedKeySpec(decoded))
        }.getOrNull()
    }

    private fun canonicalJson(element: JsonElement): String {
        return when (element) {
            is JsonObject -> element.entries
                .sortedBy { it.key }
                .joinToString(prefix = "{", postfix = "}", separator = ",") { (key, value) ->
                    "${json.encodeToString(JsonPrimitive.serializer(), JsonPrimitive(key))}:${canonicalJson(value)}"
                }

            is JsonArray -> element.joinToString(prefix = "[", postfix = "]", separator = ",") { canonicalJson(it) }
            else -> json.encodeToString(JsonElement.serializer(), element)
        }
    }

    companion object {
        const val SUPPORTED_ALGORITHM = "ECDSA_P256_SHA256"
        private const val JAVA_SIGNATURE_ALGORITHM = "SHA256withECDSA"
    }
}

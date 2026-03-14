package com.example.trackme.commands

import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Placeholder verifier that matches the backend HMAC placeholder signer.
 *
 * TODO(security): replace with asymmetric command verification rooted in the device registration key.
 */
@Singleton
class CommandSignatureVerifier @Inject constructor(
    private val json: Json,
) {
    fun verify(payloadJson: String, signature: String, algorithm: String): Boolean {
        if (algorithm != SUPPORTED_ALGORITHM) return false
        val payload = runCatching { json.parseToJsonElement(payloadJson) }.getOrNull() ?: return false
        val canonicalJson = canonicalJson(payload)
        val expected = hmacSha256Placeholder(canonicalJson)
        return expected == signature
    }

    private fun hmacSha256Placeholder(canonicalJson: String): String {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(PLACEHOLDER_SHARED_SECRET.encodeToByteArray(), "HmacSHA256"))
        return mac.doFinal(canonicalJson.encodeToByteArray()).joinToString(separator = "") { "%02x".format(it) }
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
        const val SUPPORTED_ALGORITHM = "HMAC_SHA256_PLACEHOLDER"
        private const val PLACEHOLDER_SHARED_SECRET = "trackme-dev-command-secret-change-me"
    }
}

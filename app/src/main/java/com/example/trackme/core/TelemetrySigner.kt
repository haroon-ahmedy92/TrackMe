package com.example.trackme.core

import com.example.trackme.core.security.DeviceKeyMaterialGenerator
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

interface TelemetrySigner {
    fun sign(payload: String, keyIdHint: String? = null): SignedPayload
}

data class SignedPayload(
    val signature: String,
    val algorithm: String,
    val keyId: String,
    val payloadHash: String,
)

/**
 * Signs canonical payload hashes with the enrolled device key from Android Keystore.
 *
 * The backend recomputes the same canonical hash from the parsed request body, then verifies the
 * asymmetric signature using the registered device public key.
 */
@Singleton
class KeystoreTelemetrySigner @Inject constructor(
    private val hasher: Hasher,
    private val deviceKeyMaterialGenerator: DeviceKeyMaterialGenerator,
    private val json: Json,
) : TelemetrySigner {

    override fun sign(payload: String, keyIdHint: String?): SignedPayload {
        val canonicalPayload = canonicalizePayload(payload)
        val payloadHash = hasher.sha256(canonicalPayload)
        val keyMaterial = keyIdHint
            ?.takeIf { it.isNotBlank() }
            ?.let { deviceKeyMaterialGenerator.load(it) }
            ?: deviceKeyMaterialGenerator.generateOrLoad(keyIdHint ?: DEVELOPMENT_ALIAS_SEED)
        val signature = deviceKeyMaterialGenerator.signPayloadHash(keyMaterial.keyId, payloadHash)
        return SignedPayload(
            signature = signature.signature,
            algorithm = signature.algorithm,
            keyId = signature.keyId,
            payloadHash = payloadHash,
        )
    }

    private fun canonicalizePayload(payload: String): String {
        val element = runCatching { json.parseToJsonElement(payload) }.getOrElse {
            return payload
        }
        return canonicalJson(element)
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

    private companion object {
        const val DEVELOPMENT_ALIAS_SEED = "trackme-development-device-identity"
    }
}

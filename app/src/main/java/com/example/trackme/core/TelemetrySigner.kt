package com.example.trackme.core

import javax.inject.Inject

/**
 * Placeholder signer for telemetry integrity. Replace with Android Keystore-backed signing in production.
 */
interface TelemetrySigner {
    fun sign(payload: String): SignedPayload
}

data class SignedPayload(
    val signature: String,
    val algorithm: String,
    val keyId: String,
    val payloadHash: String
)

class HashTelemetrySigner @Inject constructor(
    private val hasher: Hasher
) : TelemetrySigner {
    override fun sign(payload: String): SignedPayload {
        val payloadHash = hasher.sha256(payload)
        val keyId = "local-placeholder-key-v1"
        return SignedPayload(
            // Placeholder signature shape: SHA256(keyId:payloadHash).
            // TODO(security): replace with Android Keystore-backed asymmetric signatures.
            signature = hasher.sha256("$keyId:$payloadHash"),
            algorithm = "SHA256_KEYID_PAYLOAD_HASH_PLACEHOLDER",
            keyId = keyId,
            payloadHash = payloadHash
        )
    }
}

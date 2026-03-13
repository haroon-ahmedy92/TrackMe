package com.example.trackme.core.security

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import com.example.trackme.core.Hasher
import java.security.KeyPairGenerator
import java.security.KeyStore
import javax.inject.Inject

interface DeviceKeyMaterialGenerator {
    fun generateOrLoad(aliasSeed: String): DeviceKeyMaterial
}

data class DeviceKeyMaterial(
    val keyId: String,
    val publicKeyPem: String,
    val algorithm: String
)

/**
 * Generates a device keypair for enrollment and telemetry identity.
 *
 * This uses Android Keystore so the private key stays on-device. The server only receives the
 * public key during pairing. For local unit tests, inject a fake implementation instead.
 */
class AndroidKeystoreDeviceKeyMaterialGenerator @Inject constructor(
    private val hasher: Hasher
) : DeviceKeyMaterialGenerator {

    override fun generateOrLoad(aliasSeed: String): DeviceKeyMaterial {
        val alias = "trackme-device-" + hasher.sha256(aliasSeed).take(16)
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

        if (!keyStore.containsAlias(alias)) {
            val generator = KeyPairGenerator.getInstance(
                KeyProperties.KEY_ALGORITHM_RSA,
                ANDROID_KEYSTORE
            )
            generator.initialize(
                KeyGenParameterSpec.Builder(
                    alias,
                    KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
                )
                    .setDigests(KeyProperties.DIGEST_SHA256, KeyProperties.DIGEST_SHA512)
                    .setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PKCS1)
                    .setKeySize(2048)
                    .build()
            )
            generator.generateKeyPair()
        }

        val certificate = requireNotNull(keyStore.getCertificate(alias)) {
            "Unable to load certificate for device enrollment key $alias"
        }
        val publicKeyDer = certificate.publicKey.encoded
        return DeviceKeyMaterial(
            keyId = alias,
            publicKeyPem = publicKeyDer.toPem(),
            algorithm = "RSA"
        )
    }

    private fun ByteArray.toPem(): String {
        val base64 = Base64.encodeToString(this, Base64.NO_WRAP)
        return buildString {
            appendLine("-----BEGIN PUBLIC KEY-----")
            base64.chunked(64).forEach { appendLine(it) }
            append("-----END PUBLIC KEY-----")
        }
    }

    private companion object {
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
    }
}

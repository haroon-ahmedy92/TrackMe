package com.example.trackme.core.security

import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyInfo
import android.security.keystore.KeyProperties
import android.util.Base64
import com.example.trackme.core.Hasher
import java.security.KeyFactory
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.Signature
import java.security.cert.Certificate
import javax.inject.Inject

interface DeviceKeyMaterialGenerator {
    fun load(keyId: String): DeviceKeyMaterial?
    fun generateOrLoad(aliasSeed: String): DeviceKeyMaterial
    fun rotate(aliasSeed: String): DeviceKeyMaterial
    fun signPayloadHash(keyId: String, payloadHash: String): DeviceKeySignature
}

data class DeviceKeyMaterial(
    val keyId: String,
    val publicKeyPem: String,
    val algorithm: String,
    val isHardwareBacked: Boolean = false,
    val attestationFormat: String? = null,
    val attestationRecord: String? = null,
)

data class DeviceKeySignature(
    val keyId: String,
    val algorithm: String,
    val signature: String,
)

/**
 * Generates and uses device signing keys from Android Keystore.
 *
 * The private key never leaves the device. The backend receives the public key during enrollment or
 * rotation, then verifies signatures over canonical payload hashes.
 */
class AndroidKeystoreDeviceKeyMaterialGenerator @Inject constructor(
    private val hasher: Hasher,
) : DeviceKeyMaterialGenerator {

    override fun load(keyId: String): DeviceKeyMaterial? {
        val keyStore = keyStore()
        if (!keyStore.containsAlias(keyId)) return null
        return materialForAlias(keyStore, keyId)
    }

    override fun generateOrLoad(aliasSeed: String): DeviceKeyMaterial {
        val alias = baseAlias(aliasSeed)
        val keyStore = keyStore()
        if (!keyStore.containsAlias(alias)) {
            generateKeyPair(alias)
        }
        return materialForAlias(keyStore, alias)
    }

    override fun rotate(aliasSeed: String): DeviceKeyMaterial {
        val alias = baseAlias(aliasSeed) + "-" + System.currentTimeMillis().toString(16)
        generateKeyPair(alias)
        return materialForAlias(keyStore(), alias)
    }

    override fun signPayloadHash(keyId: String, payloadHash: String): DeviceKeySignature {
        val keyStore = keyStore()
        val entry = keyStore.getEntry(keyId, null) as? KeyStore.PrivateKeyEntry
            ?: error("No private key entry found for device key $keyId")
        val algorithm = when (entry.privateKey.algorithm.uppercase()) {
            "EC" -> ECDSA_ALGORITHM
            "RSA" -> RSA_ALGORITHM
            else -> error("Unsupported device key algorithm ${entry.privateKey.algorithm}")
        }
        val signature = Signature.getInstance(algorithm).apply {
            initSign(entry.privateKey)
            update(payloadHash.encodeToByteArray())
        }.sign()
        return DeviceKeySignature(
            keyId = keyId,
            algorithm = algorithm,
            signature = Base64.encodeToString(signature, Base64.NO_WRAP),
        )
    }

    private fun generateKeyPair(alias: String) {
        val generator = KeyPairGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_EC,
            ANDROID_KEYSTORE,
        )
        val builder = KeyGenParameterSpec.Builder(
            alias,
            KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY,
        )
            .setAlgorithmParameterSpec(java.security.spec.ECGenParameterSpec("secp256r1"))
            .setDigests(KeyProperties.DIGEST_SHA256)
            .setUserAuthenticationRequired(false)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            // Placeholder challenge so the certificate chain can later be replaced with real attestation handling.
            builder.setAttestationChallenge(hasher.sha256(alias).take(32).encodeToByteArray())
        }
        generator.initialize(builder.build())
        generator.generateKeyPair()
    }

    private fun materialForAlias(keyStore: KeyStore, alias: String): DeviceKeyMaterial {
        val certificate = requireNotNull(keyStore.getCertificate(alias)) {
            "Unable to load certificate for device key $alias"
        }
        val publicKeyDer = certificate.publicKey.encoded
        val certificateChain = keyStore.getCertificateChain(alias)?.toList().orEmpty()
        return DeviceKeyMaterial(
            keyId = alias,
            publicKeyPem = publicKeyDer.toPublicKeyPem(),
            algorithm = when (certificate.publicKey.algorithm.uppercase()) {
                "EC" -> ECDSA_ALGORITHM
                "RSA" -> RSA_ALGORITHM
                else -> certificate.publicKey.algorithm
            },
            isHardwareBacked = isHardwareBacked(alias, certificate.publicKey.algorithm),
            attestationFormat = certificateChain.takeIf { it.isNotEmpty() }?.let { ATTESTATION_FORMAT },
            attestationRecord = certificateChain.takeIf { it.isNotEmpty() }?.toPemChain(),
        )
    }

    private fun isHardwareBacked(alias: String, algorithm: String): Boolean {
        return runCatching {
            val keyStore = keyStore()
            val entry = keyStore.getEntry(alias, null) as? KeyStore.PrivateKeyEntry ?: return false
            val factory = KeyFactory.getInstance(algorithm, ANDROID_KEYSTORE)
            val keyInfo = factory.getKeySpec(entry.privateKey, KeyInfo::class.java)
            keyInfo.isInsideSecureHardware
        }.getOrDefault(false)
    }

    private fun keyStore(): KeyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

    private fun baseAlias(aliasSeed: String): String {
        return "trackme-device-" + hasher.sha256(aliasSeed).take(24)
    }

    private fun ByteArray.toPublicKeyPem(): String {
        val base64 = Base64.encodeToString(this, Base64.NO_WRAP)
        return buildString {
            appendLine("-----BEGIN PUBLIC KEY-----")
            base64.chunked(64).forEach { appendLine(it) }
            append("-----END PUBLIC KEY-----")
        }
    }

    private fun List<Certificate>.toPemChain(): String {
        return joinToString(separator = "\n") { certificate ->
            val base64 = Base64.encodeToString(certificate.encoded, Base64.NO_WRAP)
            buildString {
                appendLine("-----BEGIN CERTIFICATE-----")
                base64.chunked(64).forEach { appendLine(it) }
                append("-----END CERTIFICATE-----")
            }
        }
    }

    private companion object {
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val ECDSA_ALGORITHM = "SHA256withECDSA"
        const val RSA_ALGORITHM = "SHA256withRSA"
        const val ATTESTATION_FORMAT = "android_keystore_x509_chain"
    }
}

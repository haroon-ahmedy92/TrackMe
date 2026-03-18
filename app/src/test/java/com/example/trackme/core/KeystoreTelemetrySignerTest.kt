package com.example.trackme.core

import com.example.trackme.core.security.DeviceKeyMaterial
import com.example.trackme.core.security.DeviceKeyMaterialGenerator
import com.example.trackme.core.security.DeviceKeySignature
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class KeystoreTelemetrySignerTest {

    @Test
    fun sign_canonicalizes_json_before_hashing() {
        val generator = FakeDeviceKeyMaterialGenerator()
        val signer = KeystoreTelemetrySigner(
            hasher = Sha256Hasher(),
            deviceKeyMaterialGenerator = generator,
            json = Json { explicitNulls = false },
        )

        val first = signer.sign("""{"b":2,"a":1}""", keyIdHint = "device-key-1")
        val second = signer.sign("""{"a":1,"b":2}""", keyIdHint = "device-key-1")

        assertEquals(first.payloadHash, second.payloadHash)
        assertEquals("device-key-1", first.keyId)
        assertTrue(first.signature.startsWith("sig:"))
    }
}

private class FakeDeviceKeyMaterialGenerator : DeviceKeyMaterialGenerator {
    override fun load(keyId: String): DeviceKeyMaterial? {
        return DeviceKeyMaterial(
            keyId = keyId,
            publicKeyPem = "pem",
            algorithm = "SHA256withECDSA",
        )
    }

    override fun generateOrLoad(aliasSeed: String): DeviceKeyMaterial = requireNotNull(load(aliasSeed))

    override fun rotate(aliasSeed: String): DeviceKeyMaterial = requireNotNull(load(aliasSeed + "-rotated"))

    override fun signPayloadHash(keyId: String, payloadHash: String): DeviceKeySignature {
        return DeviceKeySignature(
            keyId = keyId,
            algorithm = "SHA256withECDSA",
            signature = "sig:$payloadHash",
        )
    }
}

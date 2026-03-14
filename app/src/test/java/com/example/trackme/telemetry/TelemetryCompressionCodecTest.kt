package com.example.trackme.telemetry

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TelemetryCompressionCodecTest {

    @Test
    fun gzipCodec_roundTripsPayload() {
        val codec = GzipTelemetryCompressionCodec()
        val payload = """{"mode":"normal","battery_percent":81,"source_methods":["fused_last_known"]}"""

        val compressed = codec.compress(payload)

        assertTrue(compressed.isNotEmpty())
        assertEquals(payload, codec.decompress(compressed))
    }
}

package com.example.trackme.telemetry

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.util.zip.GZIPInputStream
import java.util.zip.GZIPOutputStream
import javax.inject.Inject
import javax.inject.Singleton

interface TelemetryCompressionCodec {
    val algorithm: String
    fun compress(payload: String): ByteArray
    fun decompress(payload: ByteArray): String
}

@Singleton
class GzipTelemetryCompressionCodec @Inject constructor() : TelemetryCompressionCodec {
    override val algorithm: String = ALGORITHM

    override fun compress(payload: String): ByteArray {
        val output = ByteArrayOutputStream()
        GZIPOutputStream(output).bufferedWriter(Charsets.UTF_8).use { writer ->
            writer.write(payload)
        }
        return output.toByteArray()
    }

    override fun decompress(payload: ByteArray): String {
        return GZIPInputStream(ByteArrayInputStream(payload)).bufferedReader(Charsets.UTF_8).use { it.readText() }
    }

    companion object {
        const val ALGORITHM = "gzip_json_v1"
    }
}

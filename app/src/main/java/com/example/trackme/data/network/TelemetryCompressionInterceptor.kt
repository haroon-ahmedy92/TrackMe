package com.example.trackme.data.network

import java.io.ByteArrayOutputStream
import java.util.zip.GZIPOutputStream
import javax.inject.Inject
import javax.inject.Singleton
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response

@Singleton
class TelemetryCompressionInterceptor @Inject constructor() : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        if (!request.url.encodedPath.endsWith("/platform/locations/ingest-batch")) {
            return chain.proceed(request)
        }
        val body = request.body ?: return chain.proceed(request)
        if (request.header("Content-Encoding") != null) {
            return chain.proceed(request)
        }

        val buffer = okio.Buffer()
        body.writeTo(buffer)
        val compressedBytes = ByteArrayOutputStream().use { output ->
            GZIPOutputStream(output).use { gzip ->
                gzip.write(buffer.readByteArray())
            }
            output.toByteArray()
        }
        val compressedBody = compressedBytes.toRequestBody(body.contentType() ?: "application/json".toMediaTypeOrNull())
        val compressedRequest = request.newBuilder()
            .header("Content-Encoding", "gzip")
            .method(request.method, compressedBody)
            .build()
        return chain.proceed(compressedRequest)
    }
}

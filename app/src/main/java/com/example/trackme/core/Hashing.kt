package com.example.trackme.core

import java.security.MessageDigest

interface Hasher {
    fun sha256(value: String): String
}

class Sha256Hasher : Hasher {
    override fun sha256(value: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(value.toByteArray())
        return digest.joinToString(separator = "") { "%02x".format(it) }
    }
}

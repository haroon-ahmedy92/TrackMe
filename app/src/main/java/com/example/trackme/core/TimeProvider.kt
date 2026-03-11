package com.example.trackme.core

interface TimeProvider {
    fun nowEpochMillis(): Long
}

class SystemTimeProvider : TimeProvider {
    override fun nowEpochMillis(): Long = System.currentTimeMillis()
}

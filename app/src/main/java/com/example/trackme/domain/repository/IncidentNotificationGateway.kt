package com.example.trackme.domain.repository

interface IncidentNotificationGateway {
    suspend fun notifyEscalation(title: String, body: String): Result<Unit>
}

package com.example.trackme.domain.usecase

import android.os.BatteryManager
import com.example.trackme.core.TelemetrySigner
import com.example.trackme.core.TimeProvider
import com.example.trackme.data.network.CheckInTelemetryPayload
import com.example.trackme.data.network.LocationTelemetryDto
import com.example.trackme.data.network.PlatformLocationIngestRequestDto
import com.example.trackme.data.preferences.TrackingPreferencesDataSource
import com.example.trackme.domain.model.CheckInMode
import com.example.trackme.domain.model.LocationSnapshot
import com.example.trackme.domain.model.shouldCaptureOnLowBattery
import com.example.trackme.domain.model.staleAfterMillis
import com.example.trackme.domain.model.toApiValue
import com.example.trackme.domain.repository.AuditRepository
import com.example.trackme.domain.repository.DeviceStateRepository
import com.example.trackme.domain.repository.EnrollmentRepository
import com.example.trackme.domain.repository.IntegrityRepository
import com.example.trackme.domain.repository.LocationRepository
import com.example.trackme.domain.repository.TelemetrySyncRepository
import com.example.trackme.telemetry.TelemetrySyncScheduler
import kotlinx.coroutines.flow.first
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.time.Instant
import javax.inject.Inject

class PerformCheckInUseCase @Inject constructor(
    private val enrollmentRepository: EnrollmentRepository,
    private val trackingPreferences: TrackingPreferencesDataSource,
    private val deviceStateRepository: DeviceStateRepository,
    private val locationRepository: LocationRepository,
    private val integrityRepository: IntegrityRepository,
    private val auditRepository: AuditRepository,
    private val telemetrySyncRepository: TelemetrySyncRepository,
    private val telemetrySigner: TelemetrySigner,
    private val telemetrySyncScheduler: TelemetrySyncScheduler,
    private val timeProvider: TimeProvider,
    private val batteryManager: BatteryManager,
    private val json: Json
) {
    suspend operator fun invoke(mode: CheckInMode, source: String) {
        val explicitConsentGranted = trackingPreferences.explicitTrackingConsentGranted.first()
        if (!explicitConsentGranted) {
            auditRepository.appendEvent(
                type = "CHECKIN_SKIPPED",
                summary = "Check-in skipped because explicit tracking consent is not granted",
                metadata = mapOf("source" to source, "mode" to mode.name)
            )
            return
        }

        val enrollment = enrollmentRepository.observeEnrollmentStatus().first()
        if (!enrollment.isEnrolled) {
            auditRepository.appendEvent(
                type = "CHECKIN_SKIPPED",
                summary = "Check-in skipped because device is not enrolled",
                metadata = mapOf("source" to source)
            )
            return
        }

        val now = timeProvider.nowEpochMillis()
        val batteryPercent = batteryManager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
            .takeIf { it in 0..100 }

        val lowBattery = (batteryPercent ?: 100) <= LOW_BATTERY_THRESHOLD
        val locationSnapshot = if (!mode.shouldCaptureOnLowBattery() && lowBattery) {
            null
        } else {
            locationRepository.captureCurrentLocation(source)
        }
        val integrityToken = integrityRepository.getIntegrityTokenOrNull()
        val integrityVerdict = integrityToken
            ?.takeIf { it.isNotBlank() }
            ?.let { "TOKEN_PRESENT" }
            ?: "UNAVAILABLE_PLACEHOLDER"

        deviceStateRepository.updateCheckIn(mode = mode, batteryPercent = batteryPercent, checkInAtEpochMs = now)

        val telemetryPayload = CheckInTelemetryPayload(
            mode = mode.name,
            source = source,
            checkInAtEpochMs = now,
            batteryPercent = batteryPercent,
            lowBatteryOptimizationApplied = !mode.shouldCaptureOnLowBattery() && lowBattery,
            location = locationSnapshot?.toTelemetryDto(),
            integrityVerdict = integrityVerdict
        )
        val telemetryPayloadJson = json.encodeToString(telemetryPayload)
        val signedPayload = telemetrySigner.sign(telemetryPayloadJson, enrollment.keyId)
        val staleAgeMinutes = locationSnapshot
            ?.let { ((now - it.capturedAtEpochMs).coerceAtLeast(0L)) / 60_000L }
        val staleData = staleAgeMinutes != null && staleAgeMinutes * 60_000L > mode.staleAfterMillis()

        val metadata = buildMap<String, String> {
            put("mode", mode.name)
            put("source", source)
            put("batteryPercent", batteryPercent?.toString() ?: "unknown")
            put("hasLocation", (locationSnapshot != null).toString())
            put("lowBatteryOptimizationApplied", (!mode.shouldCaptureOnLowBattery() && lowBattery).toString())
            put("staleData", staleData.toString())
            staleAgeMinutes?.let { put("staleAgeMinutes", it.toString()) }
            locationSnapshot?.let { location ->
                put("locationMethod", location.methodLabel)
                put("locationApproximate", location.isApproximate.toString())
                put("locationConfidence", location.confidenceScore.toString())
                put("locationPrecision", location.precision.name)
                put("locationNetworkType", location.networkType.name)
                put("locationMotionState", location.motionState.name)
                put("locationGeofenceTransition", location.geofenceTransition ?: "none")
                put("locationSuspiciousMock", location.suspiciousMockLocation.toString())
            }
            put("integrityVerdict", integrityVerdict)
            put("integrityTokenPresent", (!integrityToken.isNullOrBlank()).toString())
            put("telemetryPayloadJson", telemetryPayloadJson)
        }

        val canQueueForBackend = !enrollment.orgId.isNullOrBlank() &&
            !enrollment.deviceId.isNullOrBlank() &&
            !enrollment.keyId.isNullOrBlank()
        if (canQueueForBackend) {
            val request = PlatformLocationIngestRequestDto(
                orgId = requireNotNull(enrollment.orgId),
                deviceId = requireNotNull(enrollment.deviceId),
                mode = mode.toApiValue(),
                idempotencyKey = "loc-${signedPayload.payloadHash.take(20)}-$now",
                capturedAt = Instant.ofEpochMilli(locationSnapshot?.capturedAtEpochMs ?: now).toString(),
                capturedAtEpochMs = locationSnapshot?.capturedAtEpochMs ?: now,
                latitude = locationSnapshot?.latitude,
                longitude = locationSnapshot?.longitude,
                accuracyMeters = locationSnapshot?.accuracyMeters,
                precision = locationSnapshot?.precision?.name?.lowercase() ?: "approximate",
                confidenceScore = locationSnapshot?.confidenceScore,
                sourceMethods = locationSnapshot
                    ?.toSourceMethods(staleData = staleData)
                    ?: listOfNotNull(
                        "checkin_without_location",
                        "low_battery_capture_skipped".takeIf { !mode.shouldCaptureOnLowBattery() && lowBattery },
                    ),
                networkType = locationSnapshot?.networkType?.name?.lowercase(),
                batteryPercent = batteryPercent,
                motionState = locationSnapshot?.motionState?.name?.lowercase(),
                telemetrySignature = signedPayload.signature,
                telemetryKeyId = signedPayload.keyId,
                telemetryPayloadHash = signedPayload.payloadHash,
                integrityVerdict = integrityVerdict,
            )
            telemetrySyncRepository.enqueue(request)
            telemetrySyncScheduler.scheduleImmediateSync()
        } else {
            auditRepository.appendEvent(
                type = "CHECKIN_QUEUE_SKIPPED",
                summary = "Telemetry queue skipped because backend identity is not verified yet",
                metadata = mapOf(
                    "source" to source,
                    "mode" to mode.name,
                    "registrationState" to enrollment.registrationState.name,
                )
            )
        }

        auditRepository.appendEvent(
            type = "CHECKIN_RECORDED",
            summary = "Device check-in captured",
            metadata = metadata + mapOf(
                "telemetrySignature" to signedPayload.signature,
                "telemetryAlgorithm" to signedPayload.algorithm,
                "telemetryKeyId" to signedPayload.keyId,
                "telemetryPayloadHash" to signedPayload.payloadHash
            )
        )
    }

    companion object {
        private const val LOW_BATTERY_THRESHOLD = 15
    }
}

private fun LocationSnapshot.toTelemetryDto(): LocationTelemetryDto {
    return LocationTelemetryDto(
        latitude = latitude,
        longitude = longitude,
        accuracyMeters = accuracyMeters,
        capturedAtEpochMs = capturedAtEpochMs,
        source = source,
        sourceSignals = sourceSignals,
        confidenceScore = confidenceScore,
        precision = precision.name,
        isApproximate = isApproximate,
        methodLabel = methodLabel,
        networkType = networkType.name,
        motionState = motionState.name,
        hashedWifiSsid = hashedWifiSsid,
        hashedWifiBssid = hashedWifiBssid,
        geofenceTransition = geofenceTransition,
        wifiRttCapable = wifiRttCapable,
        suspiciousMockLocation = suspiciousMockLocation,
        spoofingReasons = spoofingReasons
    )
}

private fun LocationSnapshot.toSourceMethods(staleData: Boolean): List<String> {
    return buildList {
        addAll(sourceSignals)
        if (staleData) add("stale_capture")
        if (suspiciousMockLocation) add("suspected_mock_location")
    }.distinct()
}

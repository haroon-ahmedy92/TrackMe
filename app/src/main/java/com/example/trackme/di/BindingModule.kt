package com.example.trackme.di

import com.example.trackme.commands.AndroidDeviceAdminCommandController
import com.example.trackme.commands.AndroidRecoveryMessageNotifier
import com.example.trackme.commands.DeviceAdminCommandController
import com.example.trackme.commands.LostModeCommandExecutor
import com.example.trackme.commands.PendingCommandProcessor
import com.example.trackme.commands.RecoveryMessageNotifier
import com.example.trackme.commands.RemoteCommandProcessor
import com.example.trackme.commands.UseCaseLostModeCommandExecutor
import com.example.trackme.compliance.CompliancePolicy
import com.example.trackme.compliance.DefaultCompliancePolicy
import com.example.trackme.core.KeystoreTelemetrySigner
import com.example.trackme.core.TelemetrySigner
import com.example.trackme.core.security.AndroidKeystoreDeviceKeyMaterialGenerator
import com.example.trackme.core.security.DeviceKeyMaterialGenerator
import com.example.trackme.data.repository.AuditRepositoryImpl
import com.example.trackme.data.repository.CommandRepositoryImpl
import com.example.trackme.feature.enrollment.DefaultEnrollmentCoordinator
import com.example.trackme.feature.enrollment.EnrollmentCoordinator
import com.example.trackme.data.repository.DeviceCapabilityRepositoryImpl
import com.example.trackme.data.repository.DeviceStateRepositoryImpl
import com.example.trackme.data.repository.DeviceManagementRepositoryImpl
import com.example.trackme.data.repository.EnrollmentRepositoryImpl
import com.example.trackme.data.repository.GeofenceRepositoryImpl
import com.example.trackme.data.repository.IntegrityRepositoryImpl
import com.example.trackme.data.repository.IncidentNotificationGatewayImpl
import com.example.trackme.data.repository.IncidentRepositoryImpl
import com.example.trackme.data.repository.LocationRepositoryImpl
import com.example.trackme.data.repository.PolicyRepositoryImpl
import com.example.trackme.data.repository.TelemetrySyncRepositoryImpl
import com.example.trackme.domain.repository.AuditRepository
import com.example.trackme.domain.repository.CommandRepository
import com.example.trackme.domain.repository.DeviceCapabilityRepository
import com.example.trackme.domain.repository.DeviceStateRepository
import com.example.trackme.domain.repository.DeviceManagementRepository
import com.example.trackme.domain.repository.EnrollmentRepository
import com.example.trackme.domain.repository.GeofenceRepository
import com.example.trackme.domain.repository.IntegrityRepository
import com.example.trackme.domain.repository.IncidentActionScheduler
import com.example.trackme.domain.repository.IncidentNotificationGateway
import com.example.trackme.domain.repository.IncidentRepository
import com.example.trackme.domain.repository.LocationRepository
import com.example.trackme.domain.repository.PolicyRepository
import com.example.trackme.domain.repository.TelemetrySyncRepository
import com.example.trackme.location.DeviceLocationProvider
import com.example.trackme.location.FusedDeviceLocationProvider
import com.example.trackme.location.GeofenceEventContextProvider
import com.example.trackme.location.IpApproximateLocationProvider
import com.example.trackme.location.InMemoryGeofenceEventContextProvider
import com.example.trackme.location.MotionContextProvider
import com.example.trackme.location.NoopIpApproximateLocationProvider
import com.example.trackme.location.AndroidNetworkContextCollector
import com.example.trackme.location.AndroidWifiRttCapabilityChecker
import com.example.trackme.location.DefaultMotionContextProvider
import com.example.trackme.location.NetworkContextCollector
import com.example.trackme.location.WifiRttCapabilityChecker
import com.example.trackme.telemetry.GzipTelemetryCompressionCodec
import com.example.trackme.telemetry.TelemetryCompressionCodec
import com.example.trackme.trust.IntegritySignalProvider
import com.example.trackme.trust.PlayIntegritySignalProvider
import com.example.trackme.worker.CheckInScheduler
import com.example.trackme.worker.CheckInSchedulerImpl
import com.example.trackme.worker.IncidentActionSchedulerImpl
import com.example.trackme.ui.map.GoogleMapProvider
import com.example.trackme.ui.map.MapProvider
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class BindingModule {

    @Binds
    @Singleton
    abstract fun bindCompliancePolicy(impl: DefaultCompliancePolicy): CompliancePolicy

    @Binds
    @Singleton
    abstract fun bindRecoveryMessageNotifier(impl: AndroidRecoveryMessageNotifier): RecoveryMessageNotifier

    @Binds
    @Singleton
    abstract fun bindDeviceAdminCommandController(impl: AndroidDeviceAdminCommandController): DeviceAdminCommandController

    @Binds
    @Singleton
    abstract fun bindLostModeCommandExecutor(impl: UseCaseLostModeCommandExecutor): LostModeCommandExecutor

    @Binds
    @Singleton
    abstract fun bindPendingCommandProcessor(impl: RemoteCommandProcessor): PendingCommandProcessor

    @Binds
    @Singleton
    abstract fun bindPolicyRepository(impl: PolicyRepositoryImpl): PolicyRepository

    @Binds
    @Singleton
    abstract fun bindEnrollmentRepository(impl: EnrollmentRepositoryImpl): EnrollmentRepository

    @Binds
    @Singleton
    abstract fun bindEnrollmentCoordinator(impl: DefaultEnrollmentCoordinator): EnrollmentCoordinator

    @Binds
    @Singleton
    abstract fun bindDeviceStateRepository(impl: DeviceStateRepositoryImpl): DeviceStateRepository

    @Binds
    @Singleton
    abstract fun bindDeviceManagementRepository(impl: DeviceManagementRepositoryImpl): DeviceManagementRepository

    @Binds
    @Singleton
    abstract fun bindDeviceCapabilityRepository(impl: DeviceCapabilityRepositoryImpl): DeviceCapabilityRepository

    @Binds
    @Singleton
    abstract fun bindLocationRepository(impl: LocationRepositoryImpl): LocationRepository

    @Binds
    @Singleton
    abstract fun bindGeofenceRepository(impl: GeofenceRepositoryImpl): GeofenceRepository

    @Binds
    @Singleton
    abstract fun bindAuditRepository(impl: AuditRepositoryImpl): AuditRepository

    @Binds
    @Singleton
    abstract fun bindCommandRepository(impl: CommandRepositoryImpl): CommandRepository

    @Binds
    @Singleton
    abstract fun bindIntegrityRepository(impl: IntegrityRepositoryImpl): IntegrityRepository

    @Binds
    @Singleton
    abstract fun bindIntegritySignalProvider(impl: PlayIntegritySignalProvider): IntegritySignalProvider

    @Binds
    @Singleton
    abstract fun bindTelemetrySyncRepository(impl: TelemetrySyncRepositoryImpl): TelemetrySyncRepository

    @Binds
    @Singleton
    abstract fun bindIncidentRepository(impl: IncidentRepositoryImpl): IncidentRepository

    @Binds
    @Singleton
    abstract fun bindIncidentNotificationGateway(
        impl: IncidentNotificationGatewayImpl
    ): IncidentNotificationGateway

    @Binds
    @Singleton
    abstract fun bindLocationProvider(impl: FusedDeviceLocationProvider): DeviceLocationProvider

    @Binds
    @Singleton
    abstract fun bindIpApproximateLocationProvider(
        impl: NoopIpApproximateLocationProvider
    ): IpApproximateLocationProvider

    @Binds
    @Singleton
    abstract fun bindNetworkContextCollector(
        impl: AndroidNetworkContextCollector
    ): NetworkContextCollector

    @Binds
    @Singleton
    abstract fun bindMotionContextProvider(
        impl: DefaultMotionContextProvider
    ): MotionContextProvider

    @Binds
    @Singleton
    abstract fun bindGeofenceEventContextProvider(
        impl: InMemoryGeofenceEventContextProvider
    ): GeofenceEventContextProvider

    @Binds
    @Singleton
    abstract fun bindWifiRttCapabilityChecker(
        impl: AndroidWifiRttCapabilityChecker
    ): WifiRttCapabilityChecker

    @Binds
    @Singleton
    abstract fun bindCheckInScheduler(impl: CheckInSchedulerImpl): CheckInScheduler

    @Binds
    @Singleton
    abstract fun bindIncidentActionScheduler(impl: IncidentActionSchedulerImpl): IncidentActionScheduler

    @Binds
    @Singleton
    abstract fun bindTelemetrySigner(impl: KeystoreTelemetrySigner): TelemetrySigner

    @Binds
    @Singleton
    abstract fun bindTelemetryCompressionCodec(impl: GzipTelemetryCompressionCodec): TelemetryCompressionCodec

    @Binds
    @Singleton
    abstract fun bindDeviceKeyMaterialGenerator(impl: AndroidKeystoreDeviceKeyMaterialGenerator): DeviceKeyMaterialGenerator

    @Binds
    @Singleton
    abstract fun bindMapProvider(impl: GoogleMapProvider): MapProvider
}

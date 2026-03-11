package com.example.trackme.di

import android.content.Context
import android.location.LocationManager
import android.net.ConnectivityManager
import android.net.wifi.WifiManager
import android.os.BatteryManager
import androidx.work.WorkManager
import com.example.trackme.core.Hasher
import com.example.trackme.core.Sha256Hasher
import com.example.trackme.core.SystemTimeProvider
import com.example.trackme.core.TimeProvider
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.FusedLocationProviderClient
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideTimeProvider(): TimeProvider = SystemTimeProvider()

    @Provides
    @Singleton
    fun provideHasher(): Hasher = Sha256Hasher()

    @Provides
    @Singleton
    fun provideJson(): Json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

    @Provides
    @Singleton
    fun provideBatteryManager(@ApplicationContext context: Context): BatteryManager {
        return context.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
    }

    @Provides
    @Singleton
    fun provideWorkManager(@ApplicationContext context: Context): WorkManager = WorkManager.getInstance(context)

    @Provides
    @Singleton
    fun provideFusedLocationProviderClient(@ApplicationContext context: Context): FusedLocationProviderClient {
        return LocationServices.getFusedLocationProviderClient(context)
    }

    @Provides
    @Singleton
    fun provideLocationManager(@ApplicationContext context: Context): LocationManager {
        return context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
    }

    @Provides
    @Singleton
    fun provideConnectivityManager(@ApplicationContext context: Context): ConnectivityManager {
        return context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
    }

    @Provides
    @Singleton
    fun provideWifiManager(@ApplicationContext context: Context): WifiManager {
        return context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
    }
}

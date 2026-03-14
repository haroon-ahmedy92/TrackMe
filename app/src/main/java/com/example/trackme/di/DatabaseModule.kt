package com.example.trackme.di

import android.content.Context
import androidx.room.Room
import com.example.trackme.data.local.TrackMeDatabase
import com.example.trackme.data.local.dao.AuditDao
import com.example.trackme.data.local.dao.DeviceCommandDao
import com.example.trackme.data.local.dao.DeviceStateDao
import com.example.trackme.data.local.dao.EnrollmentDao
import com.example.trackme.data.local.dao.IncidentDao
import com.example.trackme.data.local.dao.LocationDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): TrackMeDatabase {
        return Room.databaseBuilder(context, TrackMeDatabase::class.java, DATABASE_NAME)
            .fallbackToDestructiveMigration(dropAllTables = true)
            .build()
    }

    @Provides
    fun provideEnrollmentDao(database: TrackMeDatabase): EnrollmentDao = database.enrollmentDao()

    @Provides
    fun provideDeviceStateDao(database: TrackMeDatabase): DeviceStateDao = database.deviceStateDao()

    @Provides
    fun provideDeviceCommandDao(database: TrackMeDatabase): DeviceCommandDao = database.deviceCommandDao()

    @Provides
    fun provideLocationDao(database: TrackMeDatabase): LocationDao = database.locationDao()

    @Provides
    fun provideAuditDao(database: TrackMeDatabase): AuditDao = database.auditDao()

    @Provides
    fun provideIncidentDao(database: TrackMeDatabase): IncidentDao = database.incidentDao()

    private const val DATABASE_NAME = "trackme.db"
}

package com.example.trackme.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.data.preferences.TrackingPreferencesDataSource
import com.example.trackme.domain.repository.EnrollmentRepository
import com.example.trackme.worker.CheckInScheduler
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AppEntryViewModel @Inject constructor(
    private val enrollmentRepository: EnrollmentRepository,
    private val trackingPreferences: TrackingPreferencesDataSource,
    private val checkInScheduler: CheckInScheduler
) : ViewModel() {

    private val _isEnrolled = MutableStateFlow<Boolean?>(null)
    val isEnrolled: StateFlow<Boolean?> = _isEnrolled.asStateFlow()

    init {
        viewModelScope.launch {
            combine(
                enrollmentRepository.observeEnrollmentStatus().map { it.isEnrolled },
                trackingPreferences.explicitTrackingConsentGranted
            ) { enrolled, consentGranted ->
                enrolled && consentGranted
            }.collect { enrolled ->
                    _isEnrolled.value = enrolled
                    if (enrolled) {
                        // Idempotent unique work scheduling to keep baseline check-ins active.
                        checkInScheduler.scheduleNormalCheckIn()
                    }
                }
        }
    }
}

package com.example.trackme.ui.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.ui.common.formatEpochMillis

@Composable
fun DashboardScreen(
    paddingValues: PaddingValues,
    viewModel: DashboardViewModel = hiltViewModel()
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(text = "Recovery Dashboard", style = MaterialTheme.typography.headlineSmall)

        if (state.isLoading || state.dashboardState == null) {
            Text(text = "Loading device status...")
            return@Column
        }

        val dashboard = state.dashboardState ?: return@Column

        Card {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Enrollment", style = MaterialTheme.typography.titleMedium)
                Text("Enrolled: ${dashboard.enrollment.isEnrolled}")
                Text("Organization: ${dashboard.enrollment.organizationName ?: "Not set"}")
                Text("Consent version: ${dashboard.enrollment.consentVersion ?: "N/A"}")
                Text("Enrolled at: ${formatEpochMillis(dashboard.enrollment.enrolledAtEpochMs)}")
            }
        }

        Card {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Device State", style = MaterialTheme.typography.titleMedium)
                Text("Mode: ${dashboard.deviceState.mode}")
                Text("Last check-in: ${formatEpochMillis(dashboard.deviceState.lastCheckInEpochMs)}")
                Text("Battery: ${dashboard.deviceState.batteryPercent?.let { "$it%" } ?: "Unknown"}")
                Text("Lost mode until: ${formatEpochMillis(dashboard.deviceState.lostModeUntilEpochMs)}")
            }
        }

        Card {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Last Known Location", style = MaterialTheme.typography.titleMedium)
                val location = dashboard.lastLocation
                if (location == null) {
                    Text("No location available yet")
                } else {
                    Text("Lat/Lng: ${location.latitude}, ${location.longitude}")
                    Text("Accuracy: ${location.accuracyMeters}m")
                    Text("Captured: ${formatEpochMillis(location.capturedAtEpochMs)}")
                    Text("Source: ${location.source}")
                    Text("Method: ${location.methodLabel}")
                    Text("Approximate: ${location.isApproximate}")
                    Text("Confidence: ${location.confidenceScore}/100")
                }
            }
        }
    }
}

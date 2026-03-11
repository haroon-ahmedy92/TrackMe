package com.example.trackme.feature.status

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.R
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.feature.common.ManagedStateBanner
import com.example.trackme.ui.common.formatEpochMillis

@Composable
fun DeviceStatusScreen(
    viewModel: DeviceStatusViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ManagedStateBanner()
        Text(text = stringResource(id = R.string.device_status_title), style = MaterialTheme.typography.headlineSmall)

        when (val state = uiState) {
            AsyncUiState.Loading -> Text(stringResource(id = R.string.loading))
            is AsyncUiState.Error -> Text(state.message, color = MaterialTheme.colorScheme.error)
            is AsyncUiState.Data -> {
                val dashboard = state.value
                Card {
                    Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(stringResource(id = R.string.consent_version_label, dashboard.enrollment.consentVersion ?: "-"))
                        Text(stringResource(id = R.string.enrolled_at_label, formatEpochMillis(dashboard.enrollment.enrolledAtEpochMs)))
                        Text(stringResource(id = R.string.lost_mode_until_label, formatEpochMillis(dashboard.deviceState.lostModeUntilEpochMs)))
                        Text(stringResource(id = R.string.location_method_label, dashboard.lastLocation?.methodLabel ?: "-"))
                        Text(stringResource(id = R.string.location_confidence_label, dashboard.lastLocation?.confidenceScore?.toString() ?: "-"))
                        Text(stringResource(id = R.string.location_approximate_label, dashboard.lastLocation?.isApproximate?.toString() ?: "-"))
                    }
                }
            }
        }
    }
}

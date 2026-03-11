package com.example.trackme.feature.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
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

@Composable
fun SettingsPrivacyScreen(
    viewModel: SettingsPrivacyViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ManagedStateBanner()
        Text(text = stringResource(id = R.string.settings_privacy_title), style = MaterialTheme.typography.headlineSmall)
        Text(text = stringResource(id = R.string.settings_privacy_disclosure))

        when (val state = uiState) {
            AsyncUiState.Loading -> Text(stringResource(id = R.string.loading))
            is AsyncUiState.Error -> Text(state.message, color = MaterialTheme.colorScheme.error)
            is AsyncUiState.Data -> {
                val content = state.value
                // TODO(backend): persist full privacy policy profile per organization.
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(stringResource(id = R.string.geofence_opt_in))
                    Switch(
                        checked = content.geofenceEnabled,
                        onCheckedChange = viewModel::onGeofenceToggle
                    )
                }
                Text(stringResource(id = R.string.geofence_radius_label, content.geofenceRadiusMeters.toString()))
                Slider(
                    value = content.geofenceRadiusMeters.toFloat(),
                    onValueChange = { viewModel.onRadiusChange(it.toInt().coerceIn(100, 2000)) },
                    valueRange = 100f..2000f
                )
                Text(stringResource(id = R.string.settings_backend_todo), color = MaterialTheme.colorScheme.secondary)
                content.statusMessage?.let { Text(it) }
            }
        }
    }
}

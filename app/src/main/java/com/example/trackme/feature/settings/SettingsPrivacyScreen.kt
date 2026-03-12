package com.example.trackme.feature.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.R
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.feature.common.EmptyStateCard
import com.example.trackme.feature.common.InfoCallout
import com.example.trackme.feature.common.ManagedStateBanner
import com.example.trackme.feature.common.MetricRow
import com.example.trackme.feature.common.SectionCard
import com.example.trackme.feature.common.StatusChip
import com.example.trackme.feature.common.TrackMeScreen

@Composable
fun SettingsPrivacyScreen(
    viewModel: SettingsPrivacyViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    TrackMeScreen(
        title = stringResource(id = R.string.settings_privacy_title),
        subtitle = "Clear privacy controls for visible recovery features."
    ) {
        ManagedStateBanner()
        InfoCallout(text = stringResource(id = R.string.settings_privacy_disclosure))

        when (val state = uiState) {
            AsyncUiState.Loading -> EmptyStateCard(
                title = "Loading privacy settings",
                body = stringResource(id = R.string.loading)
            )
            is AsyncUiState.Error -> EmptyStateCard(
                title = "Settings unavailable",
                body = state.message
            )
            is AsyncUiState.Data -> {
                val content = state.value
                SectionCard(
                    title = "Geofence protection",
                    eyebrow = "Opt-in asset protection"
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = stringResource(id = R.string.geofence_opt_in),
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.weight(1f)
                        )
                        Switch(
                            checked = content.geofenceEnabled,
                            onCheckedChange = viewModel::onGeofenceToggle
                        )
                    }

                    StatusChip(
                        label = if (content.geofenceEnabled) "Protection enabled" else "Protection disabled",
                        containerColor = if (content.geofenceEnabled) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surfaceVariant,
                        contentColor = if (content.geofenceEnabled) MaterialTheme.colorScheme.onSecondaryContainer else MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    MetricRow(
                        label = "Radius",
                        value = "${content.geofenceRadiusMeters} meters",
                        emphasize = true
                    )

                    Slider(
                        value = content.geofenceRadiusMeters.toFloat(),
                        onValueChange = { viewModel.onRadiusChange(it.toInt().coerceIn(100, 2000)) },
                        valueRange = 100f..2000f
                    )
                }

                InfoCallout(text = stringResource(id = R.string.settings_backend_todo))
                content.statusMessage?.let {
                    Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

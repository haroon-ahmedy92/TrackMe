package com.example.trackme.feature.map

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.R
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.feature.common.ChipRow
import com.example.trackme.feature.common.EmptyStateCard
import com.example.trackme.feature.common.InfoCallout
import com.example.trackme.feature.common.ManagedStateBanner
import com.example.trackme.feature.common.MetricRow
import com.example.trackme.feature.common.SectionCard
import com.example.trackme.feature.common.StatusChip
import com.example.trackme.feature.common.TrackMeScreen

@Composable
fun MapScreen(
    viewModel: MapViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    TrackMeScreen(
        title = stringResource(id = R.string.map_title),
        subtitle = "Last lawful location sample, confidence, and map placeholder."
    ) {
        ManagedStateBanner()

        when (val state = uiState) {
            AsyncUiState.Loading -> EmptyStateCard(
                title = "Loading location",
                body = stringResource(id = R.string.loading)
            )
            is AsyncUiState.Error -> EmptyStateCard(
                title = "Map unavailable",
                body = state.message
            )
            is AsyncUiState.Data -> {
                val location = state.value.lastLocation
                if (location == null) {
                    EmptyStateCard(
                        title = "No location points yet",
                        body = "A marker will appear here after the first visible recovery check-in."
                    )
                } else {
                    SectionCard(
                        title = "Last known position",
                        eyebrow = "Map preview"
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(220.dp)
                                .clip(RoundedCornerShape(20.dp))
                                .background(MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.22f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(
                                modifier = Modifier.padding(20.dp),
                                verticalArrangement = Arrangement.spacedBy(10.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Text(
                                    text = "Map view placeholder",
                                    style = MaterialTheme.typography.titleMedium,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                                Text(
                                    text = viewModel.mapProvider.formatMarkerTitle(location),
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }

                        ChipRow(
                            {
                                StatusChip(
                                    label = location.precision.name.lowercase().replaceFirstChar { it.uppercase() },
                                    containerColor = MaterialTheme.colorScheme.primaryContainer,
                                    contentColor = MaterialTheme.colorScheme.onPrimaryContainer
                                )
                            },
                            {
                                StatusChip(
                                    label = "${location.confidenceScore}/100 confidence",
                                    containerColor = MaterialTheme.colorScheme.secondaryContainer,
                                    contentColor = MaterialTheme.colorScheme.onSecondaryContainer
                                )
                            }
                        )

                        MetricRow(label = "Provider", value = viewModel.mapProvider.providerName)
                        MetricRow(label = "Coordinates", value = "${location.latitude}, ${location.longitude}", emphasize = true)
                        MetricRow(label = "Accuracy", value = "${location.accuracyMeters.toInt()} meters")
                        MetricRow(label = "Method", value = location.methodLabel)
                    }
                    InfoCallout(text = stringResource(id = R.string.map_todo_backend))
                }
            }
        }
    }
}

package com.example.trackme.feature.map

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.R
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.model.LocationPrecision
import com.example.trackme.domain.model.LocationSnapshot
import com.example.trackme.feature.common.ChipRow
import com.example.trackme.feature.common.EmptyStateCard
import com.example.trackme.feature.common.InfoCallout
import com.example.trackme.feature.common.ManagedStateBanner
import com.example.trackme.feature.common.MetricRow
import com.example.trackme.feature.common.SectionCard
import com.example.trackme.feature.common.StatusChip
import com.example.trackme.feature.common.TrackMeScreen
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun MapScreen(
    viewModel: MapViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    TrackMeScreen(
        title = stringResource(id = R.string.map_title),
        subtitle = "Recent lawful location history, precision labels, and geofence context from visible recovery check-ins."
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
                val location = state.value.dashboard.lastLocation
                val history = state.value.history
                if (location == null) {
                    EmptyStateCard(
                        title = "No location points yet",
                        body = "A route and last known marker will appear here after the first visible recovery check-in."
                    )
                } else {
                    LocationHistoryMapCard(history = history)

                    SectionCard(
                        title = "Last known position",
                        eyebrow = "Current sample"
                    ) {
                        PrecisionChips(location = location)
                        MetricRow(
                            label = "Coordinates",
                            value = "${location.latitude.formatCoordinate()}, ${location.longitude.formatCoordinate()}",
                            emphasize = true
                        )
                        MetricRow(label = "Accuracy", value = "${location.accuracyMeters.toInt()} meters")
                        MetricRow(label = "Method", value = location.methodLabel)
                        MetricRow(label = "Captured", value = location.capturedAtEpochMs.toReadableTime())
                        MetricRow(label = "Signals", value = location.sourceSignals.joinToString().ifBlank { "Visible app check-in" })
                        location.geofenceTransition?.let {
                            MetricRow(label = "Geofence event", value = it.replaceFirstChar(Char::uppercase))
                        }
                    }

                    SectionCard(
                        title = "Recent points",
                        eyebrow = "Bounded playback"
                    ) {
                        if (history.isEmpty()) {
                            Text(
                                text = "No recent history samples stored locally yet.",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        } else {
                            history.takeLast(5).reversed().forEach { sample ->
                                MetricRow(
                                    label = sample.capturedAtEpochMs.toReadableTime(),
                                    value = "${sample.precision.readableLabel()} • ${sample.confidenceScore}/100"
                                )
                            }
                        }
                    }

                    InfoCallout(
                        text = "Approximate results use a separate visual style and should only be treated as area-level context. Android background limits mean the app uses bounded, visible check-ins instead of continuous hidden tracking."
                    )
                }
            }
        }
    }
}

@Composable
private fun PrecisionChips(location: LocationSnapshot) {
    ChipRow(
        {
            StatusChip(
                label = location.precision.readableLabel(),
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
        },
        {
            StatusChip(
                label = if (location.isApproximate) "Approximate source" else "Exact signal allowed",
                containerColor = MaterialTheme.colorScheme.tertiaryContainer,
                contentColor = MaterialTheme.colorScheme.onTertiaryContainer
            )
        }
    )
}

private fun Long.toReadableTime(): String {
    val formatter = SimpleDateFormat("dd MMM, HH:mm", Locale.US)
    return formatter.format(Date(this))
}

private fun Double.formatCoordinate(): String = String.format(Locale.US, "%.5f", this)

private fun LocationPrecision.readableLabel(): String = name.lowercase().replaceFirstChar { it.uppercase() }

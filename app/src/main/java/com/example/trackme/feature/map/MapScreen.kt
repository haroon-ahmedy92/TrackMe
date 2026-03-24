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
import com.example.trackme.feature.common.LocationFreshness
import com.example.trackme.feature.common.ManagedStateBanner
import com.example.trackme.feature.common.MetricRow
import com.example.trackme.feature.common.SectionCard
import com.example.trackme.feature.common.StatusChip
import com.example.trackme.feature.common.TrackMeScreen
import com.example.trackme.feature.common.freshness
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
        subtitle = stringResource(id = R.string.map_subtitle)
    ) {
        ManagedStateBanner()

        when (val state = uiState) {
            AsyncUiState.Loading -> EmptyStateCard(
                title = stringResource(id = R.string.loading_location_title),
                body = stringResource(id = R.string.loading)
            )
            is AsyncUiState.Error -> EmptyStateCard(
                title = stringResource(id = R.string.map_unavailable_title),
                body = state.message
            )
            is AsyncUiState.Data -> {
                val location = state.value.dashboard.lastLocation
                val history = state.value.history
                if (location == null) {
                    EmptyStateCard(
                        title = stringResource(id = R.string.no_location_points_title),
                        body = stringResource(id = R.string.no_location_points_body)
                    )
                } else {
                    LocationHistoryMapCard(
                        history = history,
                        mapProvider = viewModel.mapProvider
                    )

                    SectionCard(
                        title = stringResource(id = R.string.last_known_position_title),
                        eyebrow = stringResource(id = R.string.current_sample_label)
                    ) {
                        PrecisionChips(location = location)
                        MetricRow(
                            label = stringResource(id = R.string.coordinates_label),
                            value = "${location.latitude.formatCoordinate()}, ${location.longitude.formatCoordinate()}",
                            emphasize = true
                        )
                        MetricRow(label = stringResource(id = R.string.accuracy_label), value = "${location.accuracyMeters.toInt()} meters")
                        MetricRow(label = stringResource(id = R.string.method_metric_label), value = location.methodLabel)
                        MetricRow(label = stringResource(id = R.string.captured_label), value = location.capturedAtEpochMs.toReadableTime())
                        MetricRow(label = stringResource(id = R.string.signals_label), value = location.sourceSignals.joinToString().ifBlank { stringResource(id = R.string.visible_check_in_fallback) })
                        location.geofenceTransition?.let {
                            MetricRow(label = stringResource(id = R.string.geofence_event_label), value = it.replaceFirstChar(Char::uppercase))
                        }
                    }

                    SectionCard(
                        title = stringResource(id = R.string.recent_points_title),
                        eyebrow = stringResource(id = R.string.bounded_playback_label)
                    ) {
                        if (history.isEmpty()) {
                            Text(
                                text = stringResource(id = R.string.no_recent_history),
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        } else {
                            history.takeLast(5).reversed().forEach { sample ->
                                MetricRow(
                                    label = sample.capturedAtEpochMs.toReadableTime(),
                                    value = listOf(
                                        sample.precisionLabel(),
                                        stringResource(id = R.string.confidence_chip, sample.confidenceScore),
                                        sample.freshnessLabel(),
                                    ).joinToString(" • ")
                                )
                            }
                        }
                    }

                    SectionCard(
                        title = stringResource(id = R.string.signal_meanings_title),
                        eyebrow = stringResource(id = R.string.important_label)
                    ) {
                        Text(
                            text = stringResource(id = R.string.signal_meanings_body),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    InfoCallout(text = stringResource(id = R.string.signal_meaning_callout))
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
                label = location.precisionLabel(),
                containerColor = MaterialTheme.colorScheme.primaryContainer,
                contentColor = MaterialTheme.colorScheme.onPrimaryContainer
            )
        },
        {
            StatusChip(
                label = stringResource(id = R.string.confidence_chip, location.confidenceScore),
                containerColor = MaterialTheme.colorScheme.secondaryContainer,
                contentColor = MaterialTheme.colorScheme.onSecondaryContainer
            )
        },
        {
            StatusChip(
                label = when {
                    location.isApproximate -> stringResource(id = R.string.source_approximate_label)
                    else -> location.freshnessLabel()
                },
                containerColor = MaterialTheme.colorScheme.tertiaryContainer,
                contentColor = MaterialTheme.colorScheme.onTertiaryContainer
            )
        }
    )
}

@Composable
private fun LocationSnapshot.precisionLabel(): String = when (precision) {
    LocationPrecision.PRECISE -> stringResource(id = R.string.label_precise)
    LocationPrecision.MODERATE -> stringResource(id = R.string.label_moderate)
    LocationPrecision.APPROXIMATE -> stringResource(id = R.string.label_approximate)
}

@Composable
private fun LocationSnapshot.freshnessLabel(): String = when (freshness()) {
    LocationFreshness.RECENT -> stringResource(id = R.string.label_live_recent)
    LocationFreshness.STALE -> stringResource(id = R.string.label_stale)
    LocationFreshness.OFFLINE -> stringResource(id = R.string.label_offline)
}

private fun Long.toReadableTime(): String {
    val formatter = SimpleDateFormat("dd MMM, HH:mm", Locale.getDefault())
    return formatter.format(Date(this))
}

private fun Double.formatCoordinate(): String = String.format(Locale.US, "%.5f", this)

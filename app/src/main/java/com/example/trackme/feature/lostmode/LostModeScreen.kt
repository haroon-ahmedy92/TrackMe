package com.example.trackme.feature.lostmode

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
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
import com.example.trackme.ui.common.formatEpochMillis

@Composable
fun LostModeScreen(
    viewModel: LostModeViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    TrackMeScreen(
        title = stringResource(id = R.string.lost_mode_title),
        subtitle = "A visible high-frequency mode for active recovery only."
    ) {
        ManagedStateBanner()
        InfoCallout(text = stringResource(id = R.string.lost_mode_description))

        when (val state = uiState) {
            AsyncUiState.Loading -> EmptyStateCard(
                title = "Loading lost mode",
                body = stringResource(id = R.string.loading)
            )
            is AsyncUiState.Error -> EmptyStateCard(
                title = "Lost mode unavailable",
                body = state.message
            )
            is AsyncUiState.Data -> {
                val content = state.value
                SectionCard(
                    title = "Current mode",
                    eyebrow = "Recovery cadence"
                ) {
                    StatusChip(
                        label = if (content.enabled) "Lost mode active" else "Normal mode",
                        containerColor = if (content.enabled) MaterialTheme.colorScheme.tertiaryContainer else MaterialTheme.colorScheme.primaryContainer,
                        contentColor = if (content.enabled) MaterialTheme.colorScheme.onTertiaryContainer else MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    MetricRow(
                        label = "Status",
                        value = if (content.enabled) "ON" else "OFF",
                        emphasize = true
                    )
                    MetricRow(
                        label = "Ends at",
                        value = formatEpochMillis(content.untilEpochMs)
                    )
                }

                SectionCard(
                    title = "Actions",
                    eyebrow = "Time-boxed controls"
                ) {
                    Button(
                        onClick = { viewModel.enable(hours = 12) },
                        enabled = !content.inProgress,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(stringResource(id = R.string.enable_lost_mode_12h))
                    }

                    Button(
                        onClick = { viewModel.enable(hours = 24) },
                        enabled = !content.inProgress,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(stringResource(id = R.string.enable_lost_mode_24h))
                    }

                    OutlinedButton(
                        onClick = viewModel::disable,
                        enabled = content.enabled && !content.inProgress,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(stringResource(id = R.string.disable_lost_mode))
                    }

                    content.errorMessage?.let {
                        Text(it, color = MaterialTheme.colorScheme.error)
                    }
                }
            }
        }
    }
}

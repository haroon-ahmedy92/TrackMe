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
        subtitle = stringResource(id = R.string.lost_mode_subtitle)
    ) {
        ManagedStateBanner()
        InfoCallout(text = stringResource(id = R.string.lost_mode_description))

        when (val state = uiState) {
            AsyncUiState.Loading -> EmptyStateCard(
                title = stringResource(id = R.string.loading_lost_mode_title),
                body = stringResource(id = R.string.loading)
            )
            is AsyncUiState.Error -> EmptyStateCard(
                title = stringResource(id = R.string.lost_mode_unavailable_title),
                body = state.message
            )
            is AsyncUiState.Data -> {
                val content = state.value
                SectionCard(
                    title = stringResource(id = R.string.current_mode_title),
                    eyebrow = stringResource(id = R.string.recovery_cadence_label)
                ) {
                    StatusChip(
                        label = if (content.enabled) {
                            stringResource(id = R.string.lost_mode_active_label)
                        } else {
                            stringResource(id = R.string.normal_mode_label)
                        },
                        containerColor = if (content.enabled) MaterialTheme.colorScheme.tertiaryContainer else MaterialTheme.colorScheme.primaryContainer,
                        contentColor = if (content.enabled) MaterialTheme.colorScheme.onTertiaryContainer else MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    MetricRow(
                        label = stringResource(id = R.string.status_label),
                        value = if (content.enabled) "ON" else "OFF",
                        emphasize = true
                    )
                    MetricRow(
                        label = stringResource(id = R.string.ends_at_label),
                        value = formatEpochMillis(content.untilEpochMs)
                    )
                }

                SectionCard(
                    title = stringResource(id = R.string.before_enable_lost_mode_title),
                    eyebrow = stringResource(id = R.string.just_in_time_notice_label)
                ) {
                    Text(
                        text = stringResource(id = R.string.lost_mode_notice_body),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    MetricRow(
                        label = stringResource(id = R.string.user_notice_label),
                        value = stringResource(id = R.string.user_notice_value)
                    )
                    MetricRow(
                        label = stringResource(id = R.string.approximate_signals_label),
                        value = stringResource(id = R.string.approximate_signals_value)
                    )
                    MetricRow(
                        label = stringResource(id = R.string.timeout_label),
                        value = stringResource(id = R.string.timeout_value)
                    )
                }

                SectionCard(
                    title = stringResource(id = R.string.actions_title),
                    eyebrow = stringResource(id = R.string.time_boxed_controls_label)
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

                SectionCard(
                    title = stringResource(id = R.string.signal_meanings_title),
                    eyebrow = stringResource(id = R.string.important_label)
                ) {
                    Text(
                        text = stringResource(id = R.string.approximate_warning_body),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

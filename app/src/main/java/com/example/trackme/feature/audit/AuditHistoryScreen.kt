package com.example.trackme.feature.audit

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.R
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.feature.common.EmptyStateCard
import com.example.trackme.feature.common.ManagedStateBanner
import com.example.trackme.feature.common.SectionCard
import com.example.trackme.feature.common.TrackMeScreen
import com.example.trackme.ui.common.formatEpochMillis

@Composable
fun AuditHistoryScreen(
    viewModel: AuditHistoryViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    TrackMeScreen(
        title = stringResource(id = R.string.audit_title),
        subtitle = "Immutable local event history for enrollment, check-ins, and sensitive actions."
    ) {
        ManagedStateBanner()

        when (val state = uiState) {
            AsyncUiState.Loading -> EmptyStateCard(
                title = "Loading audit history",
                body = stringResource(id = R.string.loading)
            )
            is AsyncUiState.Error -> EmptyStateCard(
                title = "Audit unavailable",
                body = state.message
            )
            is AsyncUiState.Data -> {
                if (state.value.isEmpty()) {
                    EmptyStateCard(
                        title = "No audit events yet",
                        body = stringResource(id = R.string.audit_empty)
                    )
                } else {
                    Column {
                        state.value.forEach { event ->
                            SectionCard(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(bottom = 12.dp),
                                title = event.type,
                                eyebrow = formatEpochMillis(event.createdAtEpochMs)
                            ) {
                                androidx.compose.material3.Text(text = event.summary)
                                androidx.compose.material3.Text(
                                    text = "Hash: ${event.eventHash.take(20)}",
                                    style = androidx.compose.material3.MaterialTheme.typography.bodySmall,
                                    color = androidx.compose.material3.MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

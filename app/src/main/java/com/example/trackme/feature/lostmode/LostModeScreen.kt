package com.example.trackme.feature.lostmode

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
fun LostModeScreen(
    viewModel: LostModeViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ManagedStateBanner()
        Text(text = stringResource(id = R.string.lost_mode_title), style = MaterialTheme.typography.headlineSmall)
        Text(text = stringResource(id = R.string.lost_mode_description))

        when (val state = uiState) {
            AsyncUiState.Loading -> Text(stringResource(id = R.string.loading))
            is AsyncUiState.Error -> Text(state.message, color = MaterialTheme.colorScheme.error)
            is AsyncUiState.Data -> {
                val content = state.value
                Text(text = stringResource(id = R.string.lost_mode_status, if (content.enabled) "ON" else "OFF"))
                Text(text = stringResource(id = R.string.lost_mode_until_label, formatEpochMillis(content.untilEpochMs)))

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

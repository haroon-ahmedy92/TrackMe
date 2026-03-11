package com.example.trackme.ui.lostmode

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.ui.common.formatEpochMillis

@Composable
fun LostModeScreen(
    paddingValues: PaddingValues,
    viewModel: LostModeViewModel = hiltViewModel()
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(text = "Lost Mode", style = MaterialTheme.typography.headlineSmall)
        Text(
            text = "Lost mode is visible and time-boxed. Use only for device recovery incidents.",
            style = MaterialTheme.typography.bodyMedium
        )

        Card {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Status: ${if (state.isEnabled) "Enabled" else "Disabled"}")
                Text("Until: ${formatEpochMillis(state.lostModeUntilEpochMs)}")
            }
        }

        Button(
            onClick = { viewModel.enable(hours = 12) },
            modifier = Modifier.fillMaxWidth(),
            enabled = !state.isUpdating
        ) {
            Text("Enable Lost Mode (12h)")
        }

        Button(
            onClick = { viewModel.enable(hours = 24) },
            modifier = Modifier.fillMaxWidth(),
            enabled = !state.isUpdating
        ) {
            Text("Enable Lost Mode (24h)")
        }

        OutlinedButton(
            onClick = viewModel::disable,
            modifier = Modifier.fillMaxWidth(),
            enabled = state.isEnabled && !state.isUpdating
        ) {
            Text("Disable Lost Mode")
        }

        state.errorMessage?.let { error ->
            Text(text = error, color = MaterialTheme.colorScheme.error)
        }
    }
}

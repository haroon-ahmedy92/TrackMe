package com.example.trackme.feature.audit

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
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
fun AuditHistoryScreen(
    viewModel: AuditHistoryViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ManagedStateBanner()
        Text(text = stringResource(id = R.string.audit_title), style = MaterialTheme.typography.headlineSmall)

        when (val state = uiState) {
            AsyncUiState.Loading -> Text(stringResource(id = R.string.loading))
            is AsyncUiState.Error -> Text(state.message, color = MaterialTheme.colorScheme.error)
            is AsyncUiState.Data -> {
                if (state.value.isEmpty()) {
                    Text(stringResource(id = R.string.audit_empty))
                } else {
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        items(state.value, key = { it.id }) { event ->
                            Card(modifier = Modifier.fillMaxWidth()) {
                                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                    Text(text = event.type, style = MaterialTheme.typography.titleSmall)
                                    Text(text = event.summary)
                                    Text(text = formatEpochMillis(event.createdAtEpochMs))
                                    Text(text = event.eventHash.take(20))
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

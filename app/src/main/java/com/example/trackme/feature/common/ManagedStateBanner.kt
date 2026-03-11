package com.example.trackme.feature.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.example.trackme.R

@Composable
fun ManagedStateBanner() {
    Text(
        text = stringResource(id = R.string.managed_state_banner),
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.primaryContainer)
            .padding(12.dp),
        color = MaterialTheme.colorScheme.onPrimaryContainer,
        style = MaterialTheme.typography.bodyMedium
    )
}

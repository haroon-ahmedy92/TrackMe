package com.example.trackme.ui.enrollment

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@Composable
fun EnrollmentScreen(
    paddingValues: PaddingValues,
    viewModel: EnrollmentViewModel = hiltViewModel()
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            text = "Device Enrollment",
            style = MaterialTheme.typography.headlineSmall
        )

        Text(
            text = "This app is for organization-owned or explicitly enrolled devices only.",
            style = MaterialTheme.typography.bodyMedium
        )

        state.disclosure?.let { disclosure ->
            Text(text = disclosure.title, style = MaterialTheme.typography.titleMedium)
            disclosure.bulletPoints.forEach { bullet ->
                Text(text = "• $bullet", style = MaterialTheme.typography.bodyMedium)
            }
        }

        OutlinedTextField(
            value = state.organizationName,
            onValueChange = viewModel::onOrganizationNameChanged,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Organization Name") }
        )

        RowWithCheckbox(
            checked = state.consentAccepted,
            onCheckedChange = viewModel::onConsentChecked,
            text = "I consent to lawful, visible recovery tracking for this enrolled device."
        )

        state.errorMessage?.let { error ->
            Text(text = error, color = MaterialTheme.colorScheme.error)
        }

        Button(
            onClick = viewModel::enroll,
            enabled = !state.isSubmitting,
            modifier = Modifier.fillMaxWidth()
        ) {
            if (state.isSubmitting) {
                CircularProgressIndicator(strokeWidth = 2.dp)
            } else {
                Text("Enroll Device")
            }
        }

        Spacer(modifier = Modifier.height(4.dp))
    }
}

@Composable
private fun RowWithCheckbox(
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    text: String
) {
    androidx.compose.foundation.layout.Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Checkbox(checked = checked, onCheckedChange = onCheckedChange)
        Text(text = text, modifier = Modifier.weight(1f))
    }
}

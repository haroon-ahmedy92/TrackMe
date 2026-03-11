package com.example.trackme.feature.enrollment

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.R
import com.example.trackme.core.ui.AsyncUiState

@Composable
fun DeviceEnrollmentScreen(
    onEnrolled: () -> Unit,
    viewModel: EnrollmentViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    when (val state = uiState) {
        AsyncUiState.Loading -> Text(text = stringResource(id = R.string.loading))
        is AsyncUiState.Error -> Text(text = state.message, color = MaterialTheme.colorScheme.error)
        is AsyncUiState.Data -> {
            val form = state.value
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = stringResource(id = R.string.enrollment_title),
                    style = MaterialTheme.typography.headlineSmall
                )
                Text(text = viewModel.disclosure.title)
                viewModel.disclosure.bulletPoints.forEach {
                    Text(text = "• $it")
                }

                OutlinedTextField(
                    value = form.organizationName,
                    onValueChange = viewModel::onOrganizationNameChanged,
                    label = { Text(stringResource(id = R.string.organization_name)) },
                    modifier = Modifier.fillMaxWidth()
                )

                Row(modifier = Modifier.fillMaxWidth()) {
                    Checkbox(
                        checked = form.authorizationConfirmed,
                        onCheckedChange = viewModel::onAuthorizationConfirmed
                    )
                    Text(
                        text = stringResource(id = R.string.authorization_checkbox),
                        modifier = Modifier.padding(top = 12.dp)
                    )
                }

                form.errorMessage?.let {
                    Text(text = it, color = MaterialTheme.colorScheme.error)
                }

                Button(
                    onClick = { viewModel.enroll(onSuccess = onEnrolled) },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !form.isSubmitting
                ) {
                    if (form.isSubmitting) {
                        CircularProgressIndicator(strokeWidth = 2.dp)
                    } else {
                        Text(text = stringResource(id = R.string.enroll_device))
                    }
                }
            }
        }
    }
}

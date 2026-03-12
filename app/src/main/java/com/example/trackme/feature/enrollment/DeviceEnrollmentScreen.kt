package com.example.trackme.feature.enrollment

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
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
import com.example.trackme.feature.common.EmptyStateCard
import com.example.trackme.feature.common.InfoCallout
import com.example.trackme.feature.common.SectionCard
import com.example.trackme.feature.common.TrackMeScreen

@Composable
fun DeviceEnrollmentScreen(
    onEnrolled: () -> Unit,
    viewModel: EnrollmentViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    when (val state = uiState) {
        AsyncUiState.Loading -> TrackMeScreen(
            title = stringResource(id = R.string.enrollment_title),
            subtitle = "Preparing organization-owned or authorized enrollment."
        ) {
            EmptyStateCard(title = "Loading", body = stringResource(id = R.string.loading))
        }

        is AsyncUiState.Error -> TrackMeScreen(
            title = stringResource(id = R.string.enrollment_title),
            subtitle = "Preparing organization-owned or authorized enrollment."
        ) {
            EmptyStateCard(title = "Enrollment unavailable", body = state.message)
        }

        is AsyncUiState.Data -> {
            val form = state.value
            TrackMeScreen(
                title = stringResource(id = R.string.enrollment_title),
                subtitle = "Only device owners or authorized administrators should continue."
            ) {
                InfoCallout(text = viewModel.disclosure.title)

                SectionCard(
                    title = "What this enrollment means",
                    eyebrow = "Disclosure"
                ) {
                    viewModel.disclosure.bulletPoints.forEach { bullet ->
                        Text(
                            text = "• $bullet",
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }

                SectionCard(
                    title = "Organization details",
                    eyebrow = "Required fields"
                ) {
                    OutlinedTextField(
                        value = form.organizationName,
                        onValueChange = viewModel::onOrganizationNameChanged,
                        label = { Text(stringResource(id = R.string.organization_name)) },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Checkbox(
                            checked = form.authorizationConfirmed,
                            onCheckedChange = viewModel::onAuthorizationConfirmed
                        )
                        Text(
                            text = stringResource(id = R.string.authorization_checkbox),
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }

                    form.errorMessage?.let {
                        Text(text = it, color = MaterialTheme.colorScheme.error)
                    }
                }

                Button(
                    onClick = { viewModel.enroll(onSuccess = onEnrolled) },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !form.isSubmitting
                ) {
                    if (form.isSubmitting) {
                        CircularProgressIndicator(
                            strokeWidth = 2.dp,
                            color = MaterialTheme.colorScheme.onPrimary
                        )
                    } else {
                        Text(text = stringResource(id = R.string.enroll_device))
                    }
                }
            }
        }
    }
}

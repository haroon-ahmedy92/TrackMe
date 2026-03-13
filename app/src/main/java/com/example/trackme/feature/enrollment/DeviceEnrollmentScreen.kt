package com.example.trackme.feature.enrollment

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
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
import com.example.trackme.domain.model.EnrollmentAuthorizationRole
import com.example.trackme.domain.model.OwnershipType
import com.example.trackme.domain.model.PairingMethod
import com.example.trackme.feature.common.ChipRow
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
                subtitle = "Visible pairing for owner-enrolled or organization-managed devices only."
            ) {
                InfoCallout(
                    text = "This app stays visible on the phone. Locate access is enforced on the backend, limited to authorized owner/admin roles, and every lookup is audited."
                )

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
                    title = "Ownership and authorization",
                    eyebrow = "Required"
                ) {
                    Text(
                        text = "Ownership model",
                        style = MaterialTheme.typography.labelLarge
                    )
                    ChipRow(
                        {
                            FilterChip(
                                selected = form.ownershipType == OwnershipType.SINGLE_USER,
                                onClick = { viewModel.onOwnershipTypeChanged(OwnershipType.SINGLE_USER) },
                                label = { Text("Single-user owned") }
                            )
                        },
                        {
                            FilterChip(
                                selected = form.ownershipType == OwnershipType.ORGANIZATION_OWNED,
                                onClick = { viewModel.onOwnershipTypeChanged(OwnershipType.ORGANIZATION_OWNED) },
                                label = { Text("Organization-owned") }
                            )
                        }
                    )

                    Text(
                        text = "Enrollment authorized by",
                        style = MaterialTheme.typography.labelLarge
                    )
                    ChipRow(
                        {
                            FilterChip(
                                selected = form.authorizationRole == EnrollmentAuthorizationRole.OWNER,
                                onClick = { viewModel.onAuthorizationRoleChanged(EnrollmentAuthorizationRole.OWNER) },
                                label = { Text("Owner") }
                            )
                        },
                        {
                            FilterChip(
                                selected = form.authorizationRole == EnrollmentAuthorizationRole.ADMIN,
                                onClick = { viewModel.onAuthorizationRoleChanged(EnrollmentAuthorizationRole.ADMIN) },
                                label = { Text("Admin") }
                            )
                        },
                        {
                            FilterChip(
                                selected = form.authorizationRole == EnrollmentAuthorizationRole.SECURITY_OPERATOR,
                                onClick = { viewModel.onAuthorizationRoleChanged(EnrollmentAuthorizationRole.SECURITY_OPERATOR) },
                                label = { Text("Security operator") }
                            )
                        }
                    )

                    InfoCallout(
                        text = "Security operators can help with provisioning and case review, but server-side RBAC still blocks them from locating devices unless a policy-admin role authorizes that workflow."
                    )
                }

                SectionCard(
                    title = "Device and pairing",
                    eyebrow = "Registration"
                ) {
                    OutlinedTextField(
                        value = form.organizationName,
                        onValueChange = viewModel::onOrganizationNameChanged,
                        label = { Text(stringResource(id = R.string.organization_name)) },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    OutlinedTextField(
                        value = form.deviceAlias,
                        onValueChange = viewModel::onDeviceAliasChanged,
                        label = { Text("Device alias") },
                        supportingText = { Text("Shown in inventory, audit logs, and incident screens.") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    if (form.ownershipType == OwnershipType.SINGLE_USER) {
                        OutlinedTextField(
                            value = form.ownerSubject,
                            onValueChange = viewModel::onOwnerSubjectChanged,
                            label = { Text("Owner subject") },
                            supportingText = { Text("Usually the owner account ID or email used by your organization.") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                    }

                    Text(
                        text = "Pairing method",
                        style = MaterialTheme.typography.labelLarge
                    )
                    ChipRow(
                        {
                            FilterChip(
                                selected = form.pairingMethod == PairingMethod.ENROLLMENT_TOKEN,
                                onClick = { viewModel.onPairingMethodChanged(PairingMethod.ENROLLMENT_TOKEN) },
                                label = { Text("Enrollment token") }
                            )
                        },
                        {
                            FilterChip(
                                selected = form.pairingMethod == PairingMethod.QR_CODE_URI,
                                onClick = { viewModel.onPairingMethodChanged(PairingMethod.QR_CODE_URI) },
                                label = { Text("QR/link paste") }
                            )
                        }
                    )

                    OutlinedTextField(
                        value = form.pairingCredential,
                        onValueChange = viewModel::onPairingCredentialChanged,
                        label = {
                            Text(
                                if (form.pairingMethod == PairingMethod.ENROLLMENT_TOKEN) {
                                    "Enrollment token"
                                } else {
                                    "QR pairing URI"
                                }
                            )
                        },
                        supportingText = {
                            Text("Paste the token or the full trackme://pair link generated by the admin console.")
                        },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 2
                    )
                }

                SectionCard(
                    title = "Consent confirmation",
                    eyebrow = "Required"
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(
                            selected = form.authorizationConfirmed,
                            onClick = { viewModel.onAuthorizationConfirmed(!form.authorizationConfirmed) },
                            label = { Text(stringResource(id = R.string.authorization_checkbox)) }
                        )
                        Text(
                            text = "Enrollment creates a visible managed state on the device, stores an immutable audit record, and allows future locate requests only through backend policy checks.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
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

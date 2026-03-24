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
            subtitle = stringResource(id = R.string.enrollment_preparing_subtitle)
        ) {
            EmptyStateCard(
                title = stringResource(id = R.string.onboarding_loading_title),
                body = stringResource(id = R.string.loading)
            )
        }

        is AsyncUiState.Error -> TrackMeScreen(
            title = stringResource(id = R.string.enrollment_title),
            subtitle = stringResource(id = R.string.enrollment_preparing_subtitle)
        ) {
            EmptyStateCard(
                title = stringResource(id = R.string.enrollment_unavailable_title),
                body = state.message
            )
        }

        is AsyncUiState.Data -> {
            val form = state.value
            TrackMeScreen(
                title = stringResource(id = R.string.enrollment_title),
                subtitle = stringResource(id = R.string.enrollment_visible_subtitle)
            ) {
                InfoCallout(text = stringResource(id = R.string.enrollment_visibility_callout))

                SectionCard(
                    title = stringResource(id = R.string.enrollment_meaning_title),
                    eyebrow = stringResource(id = R.string.disclosure_label)
                ) {
                    viewModel.disclosure.bulletPoints.forEach { bullet ->
                        Text(
                            text = "• $bullet",
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }

                SectionCard(
                    title = stringResource(id = R.string.ownership_authorization_title),
                    eyebrow = stringResource(id = R.string.required_label)
                ) {
                    Text(
                        text = stringResource(id = R.string.ownership_model_label),
                        style = MaterialTheme.typography.labelLarge
                    )
                    ChipRow(
                        {
                            FilterChip(
                                selected = form.ownershipType == OwnershipType.SINGLE_USER,
                                onClick = { viewModel.onOwnershipTypeChanged(OwnershipType.SINGLE_USER) },
                                label = { Text(stringResource(id = R.string.ownership_single_user)) }
                            )
                        },
                        {
                            FilterChip(
                                selected = form.ownershipType == OwnershipType.ORGANIZATION_OWNED,
                                onClick = { viewModel.onOwnershipTypeChanged(OwnershipType.ORGANIZATION_OWNED) },
                                label = { Text(stringResource(id = R.string.ownership_organization_owned)) }
                            )
                        }
                    )

                    Text(
                        text = stringResource(id = R.string.authorized_by_label),
                        style = MaterialTheme.typography.labelLarge
                    )
                    ChipRow(
                        {
                            FilterChip(
                                selected = form.authorizationRole == EnrollmentAuthorizationRole.OWNER,
                                onClick = { viewModel.onAuthorizationRoleChanged(EnrollmentAuthorizationRole.OWNER) },
                                label = { Text(stringResource(id = R.string.role_owner)) }
                            )
                        },
                        {
                            FilterChip(
                                selected = form.authorizationRole == EnrollmentAuthorizationRole.ADMIN,
                                onClick = { viewModel.onAuthorizationRoleChanged(EnrollmentAuthorizationRole.ADMIN) },
                                label = { Text(stringResource(id = R.string.role_admin)) }
                            )
                        },
                        {
                            FilterChip(
                                selected = form.authorizationRole == EnrollmentAuthorizationRole.SECURITY_OPERATOR,
                                onClick = { viewModel.onAuthorizationRoleChanged(EnrollmentAuthorizationRole.SECURITY_OPERATOR) },
                                label = { Text(stringResource(id = R.string.role_security_operator)) }
                            )
                        }
                    )

                    InfoCallout(text = stringResource(id = R.string.security_operator_guidance))
                }

                SectionCard(
                    title = stringResource(id = R.string.device_pairing_title),
                    eyebrow = stringResource(id = R.string.registration_label)
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
                        label = { Text(stringResource(id = R.string.device_alias_label)) },
                        supportingText = { Text(stringResource(id = R.string.device_alias_supporting)) },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    if (form.ownershipType == OwnershipType.SINGLE_USER) {
                        OutlinedTextField(
                            value = form.ownerSubject,
                            onValueChange = viewModel::onOwnerSubjectChanged,
                            label = { Text(stringResource(id = R.string.owner_subject_label)) },
                            supportingText = { Text(stringResource(id = R.string.owner_subject_supporting)) },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                    }

                    Text(
                        text = stringResource(id = R.string.pairing_method_label),
                        style = MaterialTheme.typography.labelLarge
                    )
                    ChipRow(
                        {
                            FilterChip(
                                selected = form.pairingMethod == PairingMethod.ENROLLMENT_TOKEN,
                                onClick = { viewModel.onPairingMethodChanged(PairingMethod.ENROLLMENT_TOKEN) },
                                label = { Text(stringResource(id = R.string.pairing_method_token)) }
                            )
                        },
                        {
                            FilterChip(
                                selected = form.pairingMethod == PairingMethod.QR_CODE_URI,
                                onClick = { viewModel.onPairingMethodChanged(PairingMethod.QR_CODE_URI) },
                                label = { Text(stringResource(id = R.string.pairing_method_qr_uri)) }
                            )
                        }
                    )

                    OutlinedTextField(
                        value = form.pairingCredential,
                        onValueChange = viewModel::onPairingCredentialChanged,
                        label = {
                            Text(
                                if (form.pairingMethod == PairingMethod.ENROLLMENT_TOKEN) {
                                    stringResource(id = R.string.pairing_credential_token_label)
                                } else {
                                    stringResource(id = R.string.pairing_credential_uri_label)
                                }
                            )
                        },
                        supportingText = { Text(stringResource(id = R.string.pairing_credential_supporting)) },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 2
                    )
                }

                SectionCard(
                    title = stringResource(id = R.string.consent_confirmation_title),
                    eyebrow = stringResource(id = R.string.required_label)
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(
                            selected = form.authorizationConfirmed,
                            onClick = { viewModel.onAuthorizationConfirmed(!form.authorizationConfirmed) },
                            label = { Text(stringResource(id = R.string.authorization_checkbox)) }
                        )
                        Text(
                            text = stringResource(id = R.string.enrollment_consent_body),
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

package com.example.trackme.feature.onboarding

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.R
import com.example.trackme.core.permissions.PermissionUtils
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.feature.common.EmptyStateCard
import com.example.trackme.feature.common.InfoCallout
import com.example.trackme.feature.common.MetricRow
import com.example.trackme.feature.common.SectionCard
import com.example.trackme.feature.common.StatusChip
import com.example.trackme.feature.common.TrackMeScreen

@Composable
fun OnboardingConsentScreen(
    onContinue: () -> Unit,
    viewModel: OnboardingViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val activity = context as? Activity
    val lifecycleOwner = LocalLifecycleOwner.current

    val foregroundLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) {
        viewModel.refreshPermissions(
            foregroundGranted = PermissionUtils.hasForegroundLocation(context),
            backgroundGranted = PermissionUtils.hasBackgroundLocation(context)
        )
    }

    val backgroundLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        viewModel.setBackgroundPermissionDecision(granted)
    }

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                viewModel.refreshPermissions(
                    foregroundGranted = PermissionUtils.hasForegroundLocation(context),
                    backgroundGranted = PermissionUtils.hasBackgroundLocation(context)
                )
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    when (val state = uiState) {
        AsyncUiState.Loading -> TrackMeScreen(
            title = stringResource(id = R.string.onboarding_title),
            subtitle = stringResource(id = R.string.onboarding_preparing_subtitle)
        ) {
            EmptyStateCard(
                title = stringResource(id = R.string.onboarding_loading_title),
                body = stringResource(id = R.string.loading)
            )
        }

        is AsyncUiState.Error -> TrackMeScreen(
            title = stringResource(id = R.string.onboarding_title),
            subtitle = stringResource(id = R.string.onboarding_error_subtitle)
        ) {
            EmptyStateCard(
                title = stringResource(id = R.string.onboarding_error_title),
                body = state.message
            )
        }

        is AsyncUiState.Data -> {
            val content = state.value
            val needsBackground = PermissionUtils.requiresBackgroundLocationStep()
            val canContinue = content.consentAccepted &&
                content.foregroundLocationGranted &&
                (!needsBackground || content.backgroundLocationGranted || content.backgroundDecisionMade)

            TrackMeScreen(
                title = stringResource(id = R.string.onboarding_title),
                subtitle = stringResource(id = R.string.onboarding_description)
            ) {
                InfoCallout(text = stringResource(id = R.string.onboarding_visibility_callout))

                SectionCard(
                    title = content.disclosure?.title ?: stringResource(id = R.string.onboarding_disclosure_title),
                    eyebrow = content.disclosure?.version ?: stringResource(id = R.string.disclosure_label)
                ) {
                    content.disclosure?.bulletPoints?.forEach { bullet ->
                        Text(
                            text = "• $bullet",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                SectionCard(
                    title = stringResource(id = R.string.onboarding_background_title),
                    eyebrow = stringResource(id = R.string.onboarding_background_eyebrow)
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(
                            text = stringResource(id = R.string.onboarding_background_body),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        MetricRow(
                            label = stringResource(id = R.string.if_granted_label),
                            value = stringResource(id = R.string.if_granted_value)
                        )
                        MetricRow(
                            label = stringResource(id = R.string.if_skipped_label),
                            value = stringResource(id = R.string.if_skipped_value)
                        )
                        MetricRow(
                            label = stringResource(id = R.string.important_label),
                            value = stringResource(id = R.string.important_approximate_value),
                            emphasize = true
                        )
                    }
                }

                SectionCard(
                    title = stringResource(id = R.string.consent_confirmation_title),
                    eyebrow = stringResource(id = R.string.required_label)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Checkbox(
                            checked = content.consentAccepted,
                            onCheckedChange = { viewModel.setConsentAccepted(it) }
                        )
                        Text(
                            text = stringResource(id = R.string.consent_checkbox_label),
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }

                SectionCard(
                    title = stringResource(id = R.string.location_permissions_title),
                    eyebrow = stringResource(id = R.string.android_rules_label)
                ) {
                    StatusChip(
                        label = if (content.foregroundLocationGranted) {
                            stringResource(id = R.string.foreground_granted_short)
                        } else {
                            stringResource(id = R.string.foreground_pending_short)
                        },
                        containerColor = if (content.foregroundLocationGranted) {
                            MaterialTheme.colorScheme.secondaryContainer
                        } else {
                            MaterialTheme.colorScheme.tertiaryContainer
                        },
                        contentColor = if (content.foregroundLocationGranted) {
                            MaterialTheme.colorScheme.onSecondaryContainer
                        } else {
                            MaterialTheme.colorScheme.onTertiaryContainer
                        }
                    )

                    OutlinedButton(
                        onClick = {
                            foregroundLauncher.launch(
                                arrayOf(
                                    Manifest.permission.ACCESS_COARSE_LOCATION,
                                    Manifest.permission.ACCESS_FINE_LOCATION
                                )
                            )
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(stringResource(id = R.string.request_foreground_location))
                    }

                    Text(
                        text = if (content.foregroundLocationGranted) {
                            stringResource(id = R.string.foreground_granted)
                        } else {
                            stringResource(id = R.string.foreground_not_granted)
                        }
                    )

                    if (needsBackground && content.foregroundLocationGranted) {
                        InfoCallout(text = stringResource(id = R.string.background_guidance_callout))

                        Text(
                            text = stringResource(id = R.string.background_permission_explain),
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )

                        StatusChip(
                            label = if (content.backgroundLocationGranted) {
                                stringResource(id = R.string.background_granted_short)
                            } else {
                                stringResource(id = R.string.background_optional_short)
                            },
                            containerColor = if (content.backgroundLocationGranted) {
                                MaterialTheme.colorScheme.secondaryContainer
                            } else {
                                MaterialTheme.colorScheme.surfaceVariant
                            },
                            contentColor = if (content.backgroundLocationGranted) {
                                MaterialTheme.colorScheme.onSecondaryContainer
                            } else {
                                MaterialTheme.colorScheme.onSurfaceVariant
                            }
                        )

                        OutlinedButton(
                            onClick = {
                                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                                    val intent = Intent(
                                        Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                                        Uri.fromParts("package", context.packageName, null)
                                    )
                                    activity?.startActivity(intent)
                                } else {
                                    backgroundLauncher.launch(Manifest.permission.ACCESS_BACKGROUND_LOCATION)
                                }
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(stringResource(id = R.string.request_background_location))
                        }

                        OutlinedButton(
                            onClick = viewModel::skipBackgroundPermission,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(stringResource(id = R.string.skip_background_for_now))
                        }

                        Text(
                            text = if (content.backgroundLocationGranted) {
                                stringResource(id = R.string.background_granted)
                            } else {
                                stringResource(id = R.string.background_not_granted)
                            }
                        )
                    }
                }

                SectionCard(
                    title = stringResource(id = R.string.onboarding_next_title),
                    eyebrow = stringResource(id = R.string.visible_enrollment_label)
                ) {
                    MetricRow(
                        label = stringResource(id = R.string.onboarding_consent_record_label),
                        value = content.disclosure?.version ?: stringResource(id = R.string.pending_label)
                    )
                    MetricRow(
                        label = stringResource(id = R.string.onboarding_background_permission_label),
                        value = when {
                            !needsBackground -> stringResource(id = R.string.background_not_required_value)
                            content.backgroundLocationGranted -> stringResource(id = R.string.background_permission_granted_value)
                            content.backgroundDecisionMade -> stringResource(id = R.string.background_permission_deferred_value)
                            else -> stringResource(id = R.string.background_permission_pending_value)
                        }
                    )
                    Text(
                        text = stringResource(id = R.string.onboarding_next_body),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                SectionCard(
                    title = stringResource(id = R.string.signal_meanings_title),
                    eyebrow = stringResource(id = R.string.important_label)
                ) {
                    Text(
                        text = stringResource(id = R.string.signal_meanings_body),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Button(
                    onClick = onContinue,
                    enabled = canContinue,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(stringResource(id = R.string.continue_to_enrollment))
                }
            }
        }
    }
}

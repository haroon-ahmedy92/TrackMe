package com.example.trackme.app

import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.only
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.WindowInsetsSides
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.trackme.R
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.example.trackme.feature.audit.AuditHistoryScreen
import com.example.trackme.feature.enrollment.DeviceEnrollmentScreen
import com.example.trackme.feature.home.HomeDashboardScreen
import com.example.trackme.feature.incidents.IncidentsScreen
import com.example.trackme.feature.lostmode.LostModeScreen
import com.example.trackme.feature.map.MapScreen
import com.example.trackme.feature.onboarding.OnboardingConsentScreen
import com.example.trackme.feature.settings.SettingsPrivacyScreen
import com.example.trackme.feature.status.DeviceStatusScreen

@Composable
fun TrackMeRootApp(
    viewModel: AppShellViewModel = hiltViewModel()
) {
    val navController = rememberNavController()
    val enrolled by viewModel.isEnrolled.collectAsStateWithLifecycle()

    LaunchedEffect(enrolled) {
        when (enrolled) {
            null -> Unit
            true -> {
                viewModel.ensureNormalScheduling()
                navController.navigate(AppDestination.Home.route) {
                    popUpTo(0)
                    launchSingleTop = true
                }
            }
            false -> {
                navController.navigate(AppDestination.Onboarding.route) {
                    popUpTo(0)
                    launchSingleTop = true
                }
            }
        }
    }

    val tabs = listOf(
        TabSpec(AppDestination.Home, R.string.tab_home),
        TabSpec(AppDestination.DeviceStatus, R.string.tab_status),
        TabSpec(AppDestination.LostMode, R.string.tab_lost_mode),
        TabSpec(AppDestination.Map, R.string.tab_map),
        TabSpec(AppDestination.Incidents, R.string.tab_incidents),
        TabSpec(AppDestination.Settings, R.string.tab_settings),
        TabSpec(AppDestination.Audit, R.string.tab_audit)
    )

    Scaffold(
        bottomBar = {
            if (enrolled == true) {
                val backStack by navController.currentBackStackEntryAsState()
                val destination = backStack?.destination
                Surface(shadowElevation = 10.dp) {
                    NavigationBar(
                        windowInsets = WindowInsets.safeDrawing.only(WindowInsetsSides.Bottom),
                        tonalElevation = 0.dp
                    ) {
                        tabs.forEach { tab ->
                            NavigationBarItem(
                                selected = destination?.hierarchy?.any { it.route == tab.destination.route } == true,
                                onClick = {
                                    navController.navigate(tab.destination.route) { launchSingleTop = true }
                                },
                                icon = {
                                    Surface(
                                        shape = CircleShape,
                                        color = if (destination?.hierarchy?.any { it.route == tab.destination.route } == true) {
                                            MaterialTheme.colorScheme.primaryContainer
                                        } else {
                                            MaterialTheme.colorScheme.surfaceVariant
                                        }
                                    ) {
                                        Text(
                                            text = tab.glyph,
                                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                            style = MaterialTheme.typography.labelSmall
                                        )
                                    }
                                },
                                label = {
                                    Text(
                                        text = stringResource(id = tab.labelRes),
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                },
                                alwaysShowLabel = false,
                                colors = NavigationBarItemDefaults.colors(
                                    selectedIconColor = androidx.compose.material3.MaterialTheme.colorScheme.primary,
                                    selectedTextColor = androidx.compose.material3.MaterialTheme.colorScheme.primary,
                                    indicatorColor = androidx.compose.material3.MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.9f),
                                    unselectedIconColor = androidx.compose.material3.MaterialTheme.colorScheme.onSurfaceVariant,
                                    unselectedTextColor = androidx.compose.material3.MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            )
                        }
                    }
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = AppDestination.Onboarding.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(AppDestination.Onboarding.route) {
                OnboardingConsentScreen(
                    onContinue = { navController.navigate(AppDestination.Enrollment.route) }
                )
            }
            composable(AppDestination.Enrollment.route) {
                DeviceEnrollmentScreen(onEnrolled = {
                    navController.navigate(AppDestination.Home.route) {
                        popUpTo(AppDestination.Onboarding.route) { inclusive = true }
                        launchSingleTop = true
                    }
                })
            }
            composable(AppDestination.Home.route) { HomeDashboardScreen() }
            composable(AppDestination.DeviceStatus.route) { DeviceStatusScreen() }
            composable(AppDestination.LostMode.route) { LostModeScreen() }
            composable(AppDestination.Map.route) { MapScreen() }
            composable(AppDestination.Incidents.route) { IncidentsScreen() }
            composable(AppDestination.Settings.route) { SettingsPrivacyScreen() }
            composable(AppDestination.Audit.route) { AuditHistoryScreen() }
        }
    }
}

private data class TabSpec(
    val destination: AppDestination,
    val labelRes: Int,
    val glyph: String = when (destination) {
        AppDestination.Home -> "HM"
        AppDestination.DeviceStatus -> "ST"
        AppDestination.LostMode -> "LM"
        AppDestination.Map -> "MP"
        AppDestination.Incidents -> "IN"
        AppDestination.Settings -> "SE"
        AppDestination.Audit -> "AU"
        else -> "HM"
    }
)

package com.example.trackme.ui

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.example.trackme.ui.audit.AuditLogScreen
import com.example.trackme.ui.dashboard.DashboardScreen
import com.example.trackme.ui.enrollment.EnrollmentScreen
import com.example.trackme.ui.lostmode.LostModeScreen

@Composable
fun TrackMeApp(
    appEntryViewModel: AppEntryViewModel = hiltViewModel()
) {
    val enrolledState by appEntryViewModel.isEnrolled.collectAsStateWithLifecycle()
    val navController = rememberNavController()

    if (enrolledState == null) {
        CircularProgressIndicator()
        return
    }

    val isEnrolled = enrolledState == true

    LaunchedEffect(isEnrolled) {
        val target = if (isEnrolled) AppDestination.Dashboard.route else AppDestination.Enrollment.route
        navController.navigate(target) {
            popUpTo(navController.graph.startDestinationId) { inclusive = true }
            launchSingleTop = true
        }
    }

    val managedDestinations = listOf(AppDestination.Dashboard, AppDestination.LostMode, AppDestination.Audit)

    Scaffold(
        bottomBar = {
            if (isEnrolled) {
                val backStack by navController.currentBackStackEntryAsState()
                val currentDestination = backStack?.destination
                NavigationBar {
                    managedDestinations.forEach { destination ->
                        NavigationBarItem(
                            selected = currentDestination?.hierarchy?.any { it.route == destination.route } == true,
                            onClick = {
                                navController.navigate(destination.route) {
                                    launchSingleTop = true
                                }
                            },
                            icon = {},
                            label = { Text(destination.label) }
                        )
                    }
                }
            }
        }
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = if (isEnrolled) AppDestination.Dashboard.route else AppDestination.Enrollment.route
        ) {
            composable(AppDestination.Enrollment.route) {
                EnrollmentScreen(paddingValues = padding)
            }
            composable(AppDestination.Dashboard.route) {
                DashboardScreen(paddingValues = padding)
            }
            composable(AppDestination.LostMode.route) {
                LostModeScreen(paddingValues = padding)
            }
            composable(AppDestination.Audit.route) {
                AuditLogScreen(paddingValues = padding)
            }
        }
    }
}

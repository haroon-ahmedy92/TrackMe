package com.example.trackme.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Ocean500,
    onPrimary = Sand050,
    primaryContainer = Color(0xFFDCE7FF),
    onPrimaryContainer = Color(0xFF0D2458),
    secondary = Mint500,
    onSecondary = Sand050,
    secondaryContainer = Color(0xFFD1F1E8),
    onSecondaryContainer = Color(0xFF0E3A31),
    tertiary = Amber500,
    onTertiary = Ink900,
    tertiaryContainer = Color(0xFFF7E4BB),
    onTertiaryContainer = Color(0xFF4A340B),
    error = Crimson500,
    onError = Sand050,
    background = BlueGray050,
    onBackground = Ink900,
    surface = Sand050,
    onSurface = Ink900,
    surfaceVariant = Sand100,
    onSurfaceVariant = Color(0xFF455066),
    outline = Color(0xFFB6C0D4),
    outlineVariant = Color(0xFFD4DBE9)
)

private val DarkColors = darkColorScheme(
    primary = Ocean300,
    onPrimary = Color(0xFF072A69),
    primaryContainer = Color(0xFF123B87),
    onPrimaryContainer = Color(0xFFDDE7FF),
    secondary = Color(0xFF87D9C7),
    onSecondary = Color(0xFF00382E),
    secondaryContainer = Color(0xFF155045),
    onSecondaryContainer = Color(0xFFD1F1E8),
    tertiary = Color(0xFFF2CD7D),
    onTertiary = Color(0xFF422C00),
    tertiaryContainer = Color(0xFF614100),
    onTertiaryContainer = Color(0xFFFFE9BB),
    error = Color(0xFFFFB3B7),
    onError = Color(0xFF680019),
    errorContainer = Color(0xFF8A2535),
    onErrorContainer = Color(0xFFFFD9DC),
    background = Ink900,
    onBackground = Sand050,
    surface = Ink900,
    onSurface = Sand050,
    surfaceVariant = Ink700,
    onSurfaceVariant = Slate300,
    outline = Color(0xFF6A7386),
    outlineVariant = Color(0xFF323847)
)

@Composable
fun TrackMeTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) DarkColors else LightColors
    MaterialTheme(
        colorScheme = colors,
        typography = TrackMeTypography,
        content = content
    )
}

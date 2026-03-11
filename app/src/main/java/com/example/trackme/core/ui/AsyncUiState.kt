package com.example.trackme.core.ui

/**
 * Generic async state used by feature screens.
 * Keeping this sealed type simple helps students follow one consistent pattern.
 */
sealed interface AsyncUiState<out T> {
    data object Loading : AsyncUiState<Nothing>
    data class Data<T>(val value: T) : AsyncUiState<T>
    data class Error(val message: String) : AsyncUiState<Nothing>
}

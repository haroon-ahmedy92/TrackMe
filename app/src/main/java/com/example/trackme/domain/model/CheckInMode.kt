package com.example.trackme.domain.model

enum class CheckInMode {
    NORMAL,
    MISPLACED,
    LOST_MODE
}

fun CheckInMode.toApiValue(): String {
    return when (this) {
        CheckInMode.NORMAL -> "normal"
        CheckInMode.MISPLACED -> "misplaced"
        CheckInMode.LOST_MODE -> "lost_mode"
    }
}

fun CheckInMode.staleAfterMillis(): Long {
    return when (this) {
        CheckInMode.NORMAL -> 30 * 60_000L
        CheckInMode.MISPLACED -> 15 * 60_000L
        CheckInMode.LOST_MODE -> 5 * 60_000L
    }
}

fun CheckInMode.shouldCaptureOnLowBattery(): Boolean {
    return this != CheckInMode.NORMAL
}

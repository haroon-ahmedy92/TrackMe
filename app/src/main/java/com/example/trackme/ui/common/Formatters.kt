package com.example.trackme.ui.common

import java.text.DateFormat
import java.util.Date

fun formatEpochMillis(epochMillis: Long?): String {
    if (epochMillis == null) return "Never"
    return DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT).format(Date(epochMillis))
}

package com.example.trackme.domain.incident

import com.example.trackme.domain.model.IncidentState
import javax.inject.Inject

sealed interface IncidentTrigger {
    data object MarkSuspectedLost : IncidentTrigger
    data class ConfirmStolen(val elevatedConfirmed: Boolean) : IncidentTrigger
    data object MarkRecovered : IncidentTrigger
    data object CancelIncident : IncidentTrigger
    data object MarkWiped : IncidentTrigger
    data object Decommission : IncidentTrigger
}

class IncidentStateMachine @Inject constructor() {
    fun transition(current: IncidentState, trigger: IncidentTrigger): IncidentState {
        return when (trigger) {
            IncidentTrigger.MarkSuspectedLost -> when (current) {
                IncidentState.NORMAL, IncidentState.RECOVERED -> IncidentState.SUSPECTED_LOST
                IncidentState.SUSPECTED_LOST -> IncidentState.SUSPECTED_LOST
                IncidentState.CONFIRMED_STOLEN,
                IncidentState.WIPED,
                IncidentState.DECOMMISSIONED -> invalid(current, trigger)
            }

            is IncidentTrigger.ConfirmStolen -> {
                if (!trigger.elevatedConfirmed) {
                    throw IllegalArgumentException("Elevated confirmation is required to confirm stolen.")
                }
                when (current) {
                    IncidentState.SUSPECTED_LOST -> IncidentState.CONFIRMED_STOLEN
                    IncidentState.CONFIRMED_STOLEN -> IncidentState.CONFIRMED_STOLEN
                    else -> invalid(current, trigger)
                }
            }

            IncidentTrigger.MarkRecovered -> when (current) {
                IncidentState.SUSPECTED_LOST, IncidentState.CONFIRMED_STOLEN -> IncidentState.RECOVERED
                IncidentState.RECOVERED -> IncidentState.RECOVERED
                else -> invalid(current, trigger)
            }

            IncidentTrigger.CancelIncident -> when (current) {
                IncidentState.SUSPECTED_LOST, IncidentState.RECOVERED -> IncidentState.NORMAL
                IncidentState.NORMAL -> IncidentState.NORMAL
                else -> invalid(current, trigger)
            }

            IncidentTrigger.MarkWiped -> when (current) {
                IncidentState.CONFIRMED_STOLEN -> IncidentState.WIPED
                IncidentState.WIPED -> IncidentState.WIPED
                else -> invalid(current, trigger)
            }

            IncidentTrigger.Decommission -> when (current) {
                IncidentState.CONFIRMED_STOLEN,
                IncidentState.RECOVERED,
                IncidentState.WIPED -> IncidentState.DECOMMISSIONED
                IncidentState.DECOMMISSIONED -> IncidentState.DECOMMISSIONED
                else -> invalid(current, trigger)
            }
        }
    }

    fun canRequestRemoteLock(state: IncidentState): Boolean {
        return state == IncidentState.SUSPECTED_LOST || state == IncidentState.CONFIRMED_STOLEN
    }

    fun canRequestRemoteWipe(state: IncidentState): Boolean {
        return state == IncidentState.CONFIRMED_STOLEN
    }

    private fun invalid(current: IncidentState, trigger: IncidentTrigger): Nothing {
        throw IllegalStateException("Invalid transition: $current -> ${trigger::class.simpleName}")
    }
}

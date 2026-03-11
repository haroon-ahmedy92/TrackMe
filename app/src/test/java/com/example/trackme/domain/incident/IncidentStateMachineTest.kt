package com.example.trackme.domain.incident

import com.example.trackme.domain.model.IncidentState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class IncidentStateMachineTest {

    private val stateMachine = IncidentStateMachine()

    @Test
    fun `normal can transition to suspected lost`() {
        val next = stateMachine.transition(IncidentState.NORMAL, IncidentTrigger.MarkSuspectedLost)
        assertEquals(IncidentState.SUSPECTED_LOST, next)
    }

    @Test
    fun `confirm stolen requires elevated confirmation`() {
        val throwable = runCatching {
            stateMachine.transition(
                IncidentState.SUSPECTED_LOST,
                IncidentTrigger.ConfirmStolen(elevatedConfirmed = false)
            )
        }.exceptionOrNull()

        assertTrue(throwable is IllegalArgumentException)
    }

    @Test
    fun `suspected lost can become confirmed stolen with elevated confirmation`() {
        val next = stateMachine.transition(
            IncidentState.SUSPECTED_LOST,
            IncidentTrigger.ConfirmStolen(elevatedConfirmed = true)
        )
        assertEquals(IncidentState.CONFIRMED_STOLEN, next)
    }

    @Test
    fun `confirmed stolen can become wiped`() {
        val next = stateMachine.transition(IncidentState.CONFIRMED_STOLEN, IncidentTrigger.MarkWiped)
        assertEquals(IncidentState.WIPED, next)
    }

    @Test
    fun `invalid transition throws`() {
        val throwable = runCatching {
            stateMachine.transition(IncidentState.NORMAL, IncidentTrigger.MarkWiped)
        }.exceptionOrNull()

        assertTrue(throwable is IllegalStateException)
    }
}

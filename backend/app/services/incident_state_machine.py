from __future__ import annotations

from app.schemas.common import IncidentState


class IncidentStateMachine:
    def transition(
        self,
        current: IncidentState,
        trigger: str,
        *,
        elevated_confirmed: bool = False,
    ) -> IncidentState:
        if trigger == 'mark_suspected_lost':
            if current in {IncidentState.NORMAL, IncidentState.RECOVERED, IncidentState.SUSPECTED_LOST}:
                return IncidentState.SUSPECTED_LOST
            raise self._invalid(current, trigger)

        if trigger == 'confirm_stolen':
            if not elevated_confirmed:
                raise ValueError('Elevated confirmation is required to confirm stolen.')
            if current in {IncidentState.SUSPECTED_LOST, IncidentState.CONFIRMED_STOLEN}:
                return IncidentState.CONFIRMED_STOLEN
            raise self._invalid(current, trigger)

        if trigger == 'recover':
            if current in {IncidentState.SUSPECTED_LOST, IncidentState.CONFIRMED_STOLEN, IncidentState.RECOVERED}:
                return IncidentState.RECOVERED
            raise self._invalid(current, trigger)

        if trigger == 'cancel':
            if current in {IncidentState.NORMAL, IncidentState.SUSPECTED_LOST, IncidentState.RECOVERED}:
                return IncidentState.NORMAL
            raise self._invalid(current, trigger)

        if trigger == 'mark_wiped':
            if current in {IncidentState.CONFIRMED_STOLEN, IncidentState.WIPED}:
                return IncidentState.WIPED
            raise self._invalid(current, trigger)

        if trigger == 'decommission':
            if current in {IncidentState.CONFIRMED_STOLEN, IncidentState.RECOVERED, IncidentState.WIPED, IncidentState.DECOMMISSIONED}:
                return IncidentState.DECOMMISSIONED
            raise self._invalid(current, trigger)

        raise ValueError(f'Unknown trigger: {trigger}')

    def can_request_lock(self, state: IncidentState) -> bool:
        return state in {IncidentState.SUSPECTED_LOST, IncidentState.CONFIRMED_STOLEN}

    def can_request_wipe(self, state: IncidentState) -> bool:
        return state == IncidentState.CONFIRMED_STOLEN

    def _invalid(self, current: IncidentState, trigger: str) -> ValueError:
        return ValueError(f'Invalid transition: {current.value} -> {trigger}')

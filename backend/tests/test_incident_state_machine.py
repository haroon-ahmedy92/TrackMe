from app.schemas.common import IncidentState
from app.services.incident_state_machine import IncidentStateMachine


def test_normal_to_suspected_lost_transition() -> None:
    machine = IncidentStateMachine()
    next_state = machine.transition(IncidentState.NORMAL, 'mark_suspected_lost')
    assert next_state == IncidentState.SUSPECTED_LOST


def test_confirm_stolen_requires_elevated_confirmation() -> None:
    machine = IncidentStateMachine()
    try:
        machine.transition(IncidentState.SUSPECTED_LOST, 'confirm_stolen', elevated_confirmed=False)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_confirmed_stolen_can_be_marked_wiped() -> None:
    machine = IncidentStateMachine()
    next_state = machine.transition(IncidentState.CONFIRMED_STOLEN, 'mark_wiped', elevated_confirmed=True)
    assert next_state == IncidentState.WIPED


def test_invalid_transition_raises() -> None:
    machine = IncidentStateMachine()
    try:
        machine.transition(IncidentState.NORMAL, 'mark_wiped')
        raised = False
    except ValueError:
        raised = True
    assert raised

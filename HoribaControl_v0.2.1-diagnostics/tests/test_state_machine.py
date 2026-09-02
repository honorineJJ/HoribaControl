import pytest

from horibacontrol.core.state_machine import InvalidStateTransition, StateMachine
from horibacontrol.domain.models import InstrumentState


def test_valid_connection_sequence():
    state = StateMachine()
    state.transition(InstrumentState.CONNECTING)
    state.transition(InstrumentState.CONNECTED)
    state.transition(InstrumentState.INITIALIZING)
    state.transition(InstrumentState.READY)
    assert state.state is InstrumentState.READY


def test_invalid_transition_is_rejected():
    state = StateMachine()
    with pytest.raises(InvalidStateTransition):
        state.transition(InstrumentState.ACQUIRING)

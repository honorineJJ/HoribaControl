from __future__ import annotations

from horibacontrol.domain.models import InstrumentState


_ALLOWED: dict[InstrumentState, set[InstrumentState]] = {
    InstrumentState.DISCONNECTED: {InstrumentState.CONNECTING},
    InstrumentState.CONNECTING: {InstrumentState.CONNECTED, InstrumentState.ERROR},
    InstrumentState.CONNECTED: {
        InstrumentState.INITIALIZING,
        InstrumentState.READY,
        InstrumentState.STOPPING,
        InstrumentState.ERROR,
    },
    InstrumentState.INITIALIZING: {InstrumentState.READY, InstrumentState.ERROR},
    InstrumentState.READY: {
        InstrumentState.MOVING,
        InstrumentState.ACQUIRING,
        InstrumentState.STOPPING,
        InstrumentState.ERROR,
    },
    InstrumentState.MOVING: {InstrumentState.READY, InstrumentState.ERROR},
    InstrumentState.ACQUIRING: {InstrumentState.READY, InstrumentState.ERROR},
    InstrumentState.STOPPING: {InstrumentState.DISCONNECTED, InstrumentState.ERROR},
    InstrumentState.ERROR: {
        InstrumentState.STOPPING,
        InstrumentState.DISCONNECTED,
        InstrumentState.CONNECTING,
    },
}


class InvalidStateTransition(RuntimeError):
    pass


class StateMachine:
    def __init__(self) -> None:
        self._state = InstrumentState.DISCONNECTED

    @property
    def state(self) -> InstrumentState:
        return self._state

    def transition(self, target: InstrumentState) -> None:
        if target == self._state:
            return
        if target not in _ALLOWED[self._state]:
            raise InvalidStateTransition(
                f"Transition interdite : {self._state.value} -> {target.value}"
            )
        self._state = target

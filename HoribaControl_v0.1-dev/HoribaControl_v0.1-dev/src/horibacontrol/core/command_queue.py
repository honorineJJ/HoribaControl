from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from horibacontrol.core.event_bus import EventBus
from horibacontrol.core.state_machine import StateMachine
from horibacontrol.domain.commands import Command, CommandType
from horibacontrol.domain.events import Event
from horibacontrol.domain.models import AcquisitionSettings, InstrumentState
from horibacontrol.hardware.backend import InstrumentBackend


@dataclass(slots=True)
class _QueueItem:
    command: Command
    future: asyncio.Future[Any]


class CommandQueue:
    def __init__(
        self,
        backend: InstrumentBackend,
        state_machine: StateMachine,
        event_bus: EventBus,
        logger: logging.Logger,
    ) -> None:
        self.backend = backend
        self.state_machine = state_machine
        self.event_bus = event_bus
        self.logger = logger
        self._queue: asyncio.Queue[_QueueItem | None] = asyncio.Queue()
        self._worker: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._run(), name="HoribaControl-CommandQueue")

    async def stop(self) -> None:
        if self._worker is None:
            return
        await self._queue.put(None)
        await self._worker
        self._worker = None

    async def submit(self, command: Command) -> Any:
        if self._worker is None or self._worker.done():
            raise RuntimeError("La file de commandes n’est pas démarrée.")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        await self._queue.put(_QueueItem(command, future))
        return await future

    async def _run(self) -> None:
        while True:
            item = await self._queue.get()
            if item is None:
                self._queue.task_done()
                break
            try:
                result = await self._execute(item.command)
            except BaseException as exc:
                if not item.future.done():
                    item.future.set_exception(exc)
            else:
                if not item.future.done():
                    item.future.set_result(result)
            finally:
                self._queue.task_done()

    async def _execute(self, command: Command) -> Any:
        await self.event_bus.publish(Event("command.started", command))
        self.logger.info("Commande %s", command.type.value)
        try:
            result = await self._dispatch(command)
        except BaseException as exc:
            if command.type not in {CommandType.ABORT, CommandType.DISCONNECT}:
                try:
                    self.state_machine.transition(InstrumentState.ERROR)
                except Exception:
                    pass
            await self.event_bus.publish(Event("command.failed", {"command": command, "error": exc}))
            raise
        await self.event_bus.publish(Event("command.completed", {"command": command, "result": result}))
        return result

    async def _dispatch(self, command: Command) -> Any:
        if command.type is CommandType.CONNECT:
            self.state_machine.transition(InstrumentState.CONNECTING)
            result = await self.backend.connect()
            self.state_machine.transition(InstrumentState.CONNECTED)
            return result

        if command.type is CommandType.INITIALIZE:
            self.state_machine.transition(InstrumentState.INITIALIZING)
            await self.backend.initialize()
            self.state_machine.transition(InstrumentState.READY)
            return None

        if command.type is CommandType.MOVE:
            self.state_machine.transition(InstrumentState.MOVING)
            result = await self.backend.move_to(float(command.payload))
            self.state_machine.transition(InstrumentState.READY)
            return result

        if command.type is CommandType.ACQUIRE:
            settings = command.payload
            if not isinstance(settings, AcquisitionSettings):
                raise TypeError("La commande ACQUIRE exige AcquisitionSettings.")
            self.state_machine.transition(InstrumentState.ACQUIRING)
            result = await self.backend.acquire(settings)
            self.state_machine.transition(InstrumentState.READY)
            return result

        if command.type is CommandType.ABORT:
            await self.backend.abort()
            return None

        if command.type is CommandType.DISCONNECT:
            if self.state_machine.state is not InstrumentState.DISCONNECTED:
                self.state_machine.transition(InstrumentState.STOPPING)
                await self.backend.disconnect()
                self.state_machine.transition(InstrumentState.DISCONNECTED)
            return None

        raise ValueError(f"Commande inconnue : {command.type}")

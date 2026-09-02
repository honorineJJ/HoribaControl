from __future__ import annotations

import inspect
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from horibacontrol.domain.events import Event

EventHandler = Callable[[Event], Any | Awaitable[Any]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        if handler not in self._handlers[event_name]:
            self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        if handler in self._handlers[event_name]:
            self._handlers[event_name].remove(handler)

    async def publish(self, event: Event) -> None:
        handlers = tuple(self._handlers.get(event.name, ()))
        wildcard_handlers = tuple(self._handlers.get("*", ()))
        for handler in (*handlers, *wildcard_handlers):
            result = handler(event)
            if inspect.isawaitable(result):
                await result

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Coroutine, Any


class AsyncRunner:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, name="MicroHR-Async", daemon=True)
        self.thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def submit(self, coroutine: Coroutine[Any, Any, Any]) -> Future:
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop)

    def close(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)

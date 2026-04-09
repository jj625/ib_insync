import asyncio
import time
from typing import Any, Callable, Awaitable, List


class AsyncDebouncer:
    def __init__(
        self,
        flush_func: Callable[[List[Any]], Awaitable[None]],
        debounce: float = 0.5,
        max_wait: float = 3.0,
        max_batch: int = 20,
    ):
        """
        flush_func: async function that receives a list of items
        debounce: flush after this much quiet time
        max_wait: flush even if items keep coming
        max_batch: flush immediately if buffer reaches this size
        """
        self.flush_func = flush_func
        self.debounce = debounce
        self.max_wait = max_wait
        self.max_batch = max_batch

        self.buffer: List[Any] = []
        self.first_event: float | None = None
        self.last_event: float | None = None

        self._event = asyncio.Event()
        self._stop = False
        self._task = None
        self._lock = asyncio.Lock()

    # ---------------------------------------------------------
    # Async context manager
    # ---------------------------------------------------------
    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stop()

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------
    async def start(self):
        if self._task:
            return
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._stop = True
        self._event.set()
        if self._task:
            await self._task
        await self._flush()  # final flush

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
    async def add(self, item: Any):
        async with self._lock:
            now = time.time()
            if not self.buffer:
                self.first_event = now
            self.last_event = now
            self.buffer.append(item)

        self._event.set()  # wake worker

    # ---------------------------------------------------------
    # Worker loop
    # ---------------------------------------------------------
    async def _run(self):
        while not self._stop:
            await self._event.wait()
            self._event.clear()

            while True:
                async with self._lock:
                    if not self.buffer:
                        break

                    now = time.time()
                    quiet = now - self.last_event
                    age = now - self.first_event
                    size = len(self.buffer)

                    if quiet >= self.debounce or age >= self.max_wait or size >= self.max_batch:
                        break

                    remaining = self.debounce - quiet

                try:
                    await asyncio.wait_for(self._event.wait(), timeout=remaining)
                    self._event.clear()
                except asyncio.TimeoutError:
                    break

            await self._flush()

    # ---------------------------------------------------------
    # Flush
    # ---------------------------------------------------------
    async def _flush(self):
        async with self._lock:
            if not self.buffer:
                return
            items = self.buffer[:]
            self.buffer.clear()
            self.first_event = None
            self.last_event = None

        await self.flush_func(items)
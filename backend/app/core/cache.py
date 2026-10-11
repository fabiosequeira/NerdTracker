"""Tiny in-memory TTL cache with request coalescing.

Used for the search endpoints: the frontend fires up to six upstream searches per keystroke
pause, and people retype / backspace constantly. Caching successful results for a few minutes
removes most of that traffic, and coalescing makes N identical in-flight requests share one
upstream call. Failures are never cached.
"""
import asyncio
import time
from collections import OrderedDict
from typing import Any, Awaitable, Callable, Hashable

_MISSING = object()


class TTLCache:
    def __init__(self, ttl: float = 300.0, maxsize: int = 256):
        self.ttl = ttl
        self.maxsize = maxsize
        self._data: "OrderedDict[Hashable, tuple[float, Any]]" = OrderedDict()
        self._inflight: dict[Hashable, "asyncio.Future[Any]"] = {}

    def _get(self, key: Hashable) -> Any:
        item = self._data.get(key)
        if item is None:
            return _MISSING
        expires, value = item
        if expires < time.monotonic():
            self._data.pop(key, None)
            return _MISSING
        self._data.move_to_end(key)
        return value

    def _set(self, key: Hashable, value: Any) -> None:
        self._data[key] = (time.monotonic() + self.ttl, value)
        self._data.move_to_end(key)
        while len(self._data) > self.maxsize:
            self._data.popitem(last=False)

    async def get_or_load(self, key: Hashable, loader: Callable[[], Awaitable[Any]]) -> Any:
        hit = self._get(key)
        if hit is not _MISSING:
            return hit

        task = self._inflight.get(key)
        if task is None:
            task = asyncio.ensure_future(loader())
            self._inflight[key] = task

            def _done(t: "asyncio.Future[Any]", key: Hashable = key) -> None:
                self._inflight.pop(key, None)
                if not t.cancelled() and t.exception() is None:
                    self._set(key, t.result())

            task.add_done_callback(_done)

        # shield: one caller disconnecting must not cancel the shared upstream request
        return await asyncio.shield(task)

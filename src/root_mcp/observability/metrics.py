"""Small in-process metrics registry for operational counters."""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from threading import Lock
from typing import Iterator


class MetricsRegistry:
    """Thread-safe process-local counters used by the server."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Counter[str] = Counter()

    @contextmanager
    def running_call(self) -> Iterator[None]:
        """Track one currently running tool call."""
        self.increment("running_calls")
        try:
            yield
        finally:
            self.increment("running_calls", -1)

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter by *value*."""
        with self._lock:
            self._counters[name] += value

    def add_exported_bytes(self, value: int | None) -> None:
        """Add exported bytes when a tool reports an output size."""
        if value is not None:
            self.increment("bytes_exported", value)

    def snapshot(self) -> dict[str, int]:
        """Return a copy of current metrics counters."""
        with self._lock:
            return dict(self._counters)

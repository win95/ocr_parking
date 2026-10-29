"""Frame iteration with optional drop-on-backlog."""

from __future__ import annotations

from collections import deque
from typing import Callable, Iterator

from smart_parking.ingest.read_guard import read_with_timeout
from smart_parking.ingest.sources import FrameSource
from smart_parking.types import FrameContext


class FrameLoop:
    """Iterate frames; when max_queue>1, drop oldest and notify via on_drop."""

    def __init__(
        self,
        source: FrameSource,
        max_queue: int = 1,
        drop_when_busy: bool = True,
        on_drop: Callable[[], None] | None = None,
        read_timeout_ms: float | None = None,
    ) -> None:
        self._source = source
        self._max_queue = max(1, max_queue)
        self._on_drop = on_drop
        self._read_timeout_ms = read_timeout_ms
        self._buffer: deque[FrameContext] = deque(maxlen=self._max_queue)

    @property
    def queue_depth(self) -> int:
        if self._max_queue <= 1:
            return 0
        return len(self._buffer)

    def __iter__(self) -> Iterator[FrameContext]:
        while True:
            ctx = self._read_one()
            if ctx is None:
                break
            if self._max_queue == 1:
                yield ctx
                continue
            if len(self._buffer) >= self._max_queue and self._on_drop:
                self._on_drop()
            self._buffer.append(ctx)
            while len(self._buffer) > 1:
                if self._on_drop:
                    self._on_drop()
                self._buffer.popleft()
            yield self._buffer[-1]

    def _read_one(self) -> FrameContext | None:
        if (
            self._read_timeout_ms
            and self._read_timeout_ms > 0
            and self._source.is_live
        ):
            return read_with_timeout(self._source, self._read_timeout_ms)
        return self._source.read()

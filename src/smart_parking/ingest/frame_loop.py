"""Frame iteration with optional drop-on-backlog."""

from __future__ import annotations

from collections import deque
from typing import Callable, Iterator

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
    ) -> None:
        self._source = source
        self._max_queue = max(1, max_queue)
        self._on_drop = on_drop
        self._buffer: deque[FrameContext] = deque(maxlen=self._max_queue)

    def __iter__(self) -> Iterator[FrameContext]:
        while True:
            ctx = self._source.read()
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

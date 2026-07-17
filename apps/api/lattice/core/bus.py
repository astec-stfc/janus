import asyncio
from typing import Any


class EventBus:
    """In-process fan-out bus: delivers a copy of each incoming kafka event to every
    subscriber. One asyncio.Queue per subscriber (browser tab)
    """

    def __init__(self, maxsize: int = 8) -> None:
        self._maxsize = maxsize
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._maxsize)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(q)

    def publish(self, event: str, data: dict[str, Any]) -> None:
        """Deliver event (topic) and data to all active subscribers. (Each tab on frontend
        is a subscriber.)
        """
        message: dict[str, Any] = {"event": event, "data": data}
        for q in list(self._subscribers):
            if q.full():
                try:
                    q.get_nowait() # pop oldest one
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                pass

import asyncio
import json
from typing import Any
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from core.singletons import event_bus

router = APIRouter(prefix="/events", tags=["Events"])


def format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("")
async def stream_events(request: Request) -> StreamingResponse:
    """SSE streaming endpoint — delivers EventBus messages to browser clients."""
    q = event_bus.subscribe()

    async def event_stream():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield format_sse(message["event"], message["data"])
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            event_bus.unsubscribe(q)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

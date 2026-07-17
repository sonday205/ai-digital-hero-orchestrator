from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

import websockets
from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

from app.config import Settings


logger = logging.getLogger(__name__)


async def proxy_voice(websocket: WebSocket, character_id: str, settings: Settings) -> None:
    """Chuyển nguyên vẹn binary PCM và event transcript giữa browser và LLM."""
    await websocket.accept()
    if character_id != settings.character_id:
        await websocket.send_json(
            {"type": "error", "code": "invalid_character", "message": "Nhân vật chưa được hỗ trợ."}
        )
        await websocket.close(code=1008)
        return

    upstream_url = (
        f"{settings.llm_ws_base_url}/v1/characters/{settings.character_id}/voice"
    )
    try:
        async with websockets.connect(
            upstream_url,
            open_timeout=settings.voice_connect_timeout_seconds,
            max_size=None,
        ) as upstream:
            browser_to_llm = asyncio.create_task(_browser_to_llm(websocket, upstream))
            llm_to_browser = asyncio.create_task(_llm_to_browser(websocket, upstream))
            done, pending = await asyncio.wait(
                {browser_to_llm, llm_to_browser},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                task.result()
    except (WebSocketDisconnect, ConnectionClosed):
        return
    except Exception as exc:
        logger.warning("Voice proxy unavailable: %s", type(exc).__name__)
        with suppress(Exception):
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "voice_upstream_unavailable",
                    "message": "Không kết nối được dịch vụ nhận diện giọng nói.",
                }
            )
            await websocket.close(code=1011)


async def _browser_to_llm(websocket: WebSocket, upstream) -> None:
    while True:
        event = await websocket.receive()
        if event["type"] == "websocket.disconnect":
            return
        if event.get("bytes") is not None:
            await upstream.send(event["bytes"])
        elif event.get("text") is not None:
            await upstream.send(event["text"])


async def _llm_to_browser(websocket: WebSocket, upstream) -> None:
    async for message in upstream:
        if isinstance(message, bytes):
            await websocket.send_bytes(message)
        else:
            await websocket.send_text(message)

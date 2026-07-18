from pathlib import Path
import json

import httpx
import pytest

from app.clients import UpstreamClients, UpstreamServiceError
from app.config import Settings


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        llm_base_url="http://llm:8005",
        llm_ws_base_url="ws://llm:8005",
        tts_base_url="http://tts:8989",
        lipsync_base_url="http://lipsync:8990",
        poll_interval_seconds=0.1,
        tts_timeout_seconds=1,
        lipsync_timeout_seconds=1,
        storage_dir=tmp_path,
    )


@pytest.mark.asyncio
async def test_character_mapping_is_forwarded_to_all_upstreams(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content) if request.content else {}
        if request.url.path.endswith("/v1/characters/vo_thi_sau/chat"):
            captured["llm_path"] = request.url.path
            return httpx.Response(200, json={"answer": "Chị chào em.", "request_id": "llm-1"})
        if request.url.path.endswith("/api/v1/tts/generate"):
            captured["voice_id"] = payload.get("voice_id")
            return httpx.Response(200, json={"task_id": "tts-1", "status": "processing"})
        if request.url.path.endswith("/api/v1/lipsync/generate"):
            captured["image_id"] = payload.get("image_id")
            return httpx.Response(200, json={"task_id": "lip-1", "job_id": "job-1"})
        if request.method == "DELETE" and request.url.path.endswith(
            "/v1/characters/vo_thi_sau/sessions/demo-session-002"
        ):
            captured["delete_path"] = request.url.path
            return httpx.Response(200, json={"session_id": "demo-session-002", "deleted": True})
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        clients = UpstreamClients(make_settings(tmp_path), http)
        await clients.ask_llm("demo-session-002", "Xin chào", "vo_thi_sau")
        await clients.start_tts("Chị chào em.", "002")
        await clients.start_lipsync("/dev/shm/audio/tts-1.wav", "002")
        deleted = await clients.delete_llm_session("vo_thi_sau", "demo-session-002")

    assert deleted is True
    assert captured == {
        "llm_path": "/v1/characters/vo_thi_sau/chat",
        "voice_id": "002",
        "image_id": "002",
        "delete_path": "/v1/characters/vo_thi_sau/sessions/demo-session-002",
    }


@pytest.mark.asyncio
async def test_tts_polling_returns_shared_audio_path(tmp_path: Path) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(200, json={"task_id": "tts-1", "status": "processing"})
        return httpx.Response(
            200,
            json={"task_id": "tts-1", "status": "success", "audio_path": "/dev/shm/audio/tts-1.wav"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        clients = UpstreamClients(make_settings(tmp_path), http)
        audio_path = await clients.wait_for_tts("tts-1")

    assert audio_path == "/dev/shm/audio/tts-1.wav"
    assert attempts == 2


@pytest.mark.asyncio
async def test_tts_success_without_audio_is_rejected(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"status": "success", "message": "missing file"})
    )
    async with httpx.AsyncClient(transport=transport) as http:
        clients = UpstreamClients(make_settings(tmp_path), http)
        with pytest.raises(UpstreamServiceError, match="missing file"):
            await clients.wait_for_tts("tts-1")


@pytest.mark.asyncio
async def test_signed_video_url_uses_configured_lipsync_host(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={
                "download_url": "http://127.0.0.1:8990/api/v1/lipsync/jobs/job-1/video?expires=1&signature=abc"
            },
        )
    )
    async with httpx.AsyncClient(transport=transport) as http:
        clients = UpstreamClients(make_settings(tmp_path), http)
        url = await clients.create_video_download_url("job-1", "task-1")

    assert url.startswith("http://lipsync:8990/api/v1/lipsync/jobs/job-1/video?")

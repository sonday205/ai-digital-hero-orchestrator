import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class SuccessfulUpstreams:
    async def ask_llm(self, session_id: str, message: str):
        return "Chú sinh năm 1924 tại Thanh Hóa.", "request-1"

    async def start_tts(self, text: str):
        return "tts-task-1"

    async def wait_for_tts(self, task_id: str):
        return "/dev/shm/audio/tts-task-1.wav"

    async def start_lipsync(self, audio_path: str):
        return "lipsync-task-1", "a" * 32

    async def wait_for_lipsync(self, task_id: str):
        return {"status": "completed"}

    async def create_video_download_url(self, lipsync_job_id: str, task_id: str):
        return "http://lipsync/video"

    async def download_video(self, download_url: str, target: Path):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake-mp4")


def test_character_image_uses_configured_absolute_path(tmp_path: Path) -> None:
    image = tmp_path / "character.jpg"
    image.write_bytes(b"\xff\xd8\xffconfigured-image")
    app = create_app(
        Settings(
            storage_dir=tmp_path / "storage",
            frontend_dist_dir=tmp_path / "frontend",
            character_image_path=image,
        )
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/character/image")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/jpeg")
    assert response.headers["cache-control"] == "no-store"
    assert response.content == image.read_bytes()


def test_talk_api_exposes_downloadable_video_after_pipeline(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            storage_dir=tmp_path / "storage",
            frontend_dist_dir=tmp_path / "frontend",
        )
    )

    with TestClient(app) as client:
        app.state.orchestrator.clients = SuccessfulUpstreams()
        accepted = client.post(
            "/api/v1/talk",
            json={
                "session_id": "demo-session-001",
                "message": "Chú sinh năm bao nhiêu?",
            },
        )
        assert accepted.status_code == 202
        job_id = accepted.json()["job_id"]

        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            job = client.get(f"/api/v1/jobs/{job_id}")
            if job.json()["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)

        payload = job.json()
        assert payload["status"] == "completed"
        assert payload["answer"] == "Chú sinh năm 1924 tại Thanh Hóa."
        assert payload["video_url"] == f"/api/v1/jobs/{job_id}/video"

        video = client.get(payload["video_url"])
        assert video.status_code == 200
        assert video.headers["content-type"].startswith("video/mp4")
        assert video.content == b"fake-mp4"

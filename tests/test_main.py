import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class SuccessfulUpstreams:
    async def ask_llm(self, session_id: str, message: str, character_id: str | None = None):
        return "Chú sinh năm 1924 tại Thanh Hóa.", "request-1"

    async def start_tts(self, text: str, voice_id: str | None = None):
        return "tts-task-1"

    async def wait_for_tts(self, task_id: str):
        return "/dev/shm/audio/tts-task-1.wav"

    async def start_lipsync(self, audio_path: str, image_id: str | None = None):
        return "lipsync-task-1", "a" * 32

    async def wait_for_lipsync(self, task_id: str):
        return {"status": "completed"}

    async def create_video_download_url(self, lipsync_job_id: str, task_id: str):
        return "http://lipsync/video"

    async def download_video(self, download_url: str, target: Path):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake-mp4")


class SessionDeleteUpstream:
    def __init__(self) -> None:
        self.deleted: tuple[str, str] | None = None

    async def delete_llm_session(self, character_id: str, session_id: str) -> bool:
        self.deleted = (character_id, session_id)
        return True


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


def test_character_api_lists_both_profiles_and_serves_vo_thi_sau_image(tmp_path: Path) -> None:
    to_vinh_dien_image = tmp_path / "001.jpg"
    vo_thi_sau_image = tmp_path / "002.jpg"
    to_vinh_dien_image.write_bytes(b"\xff\xd8\xffto-vinh-dien")
    vo_thi_sau_image.write_bytes(b"\xff\xd8\xffvo-thi-sau")
    app = create_app(
        Settings(
            storage_dir=tmp_path / "storage",
            frontend_dist_dir=tmp_path / "frontend",
            character_image_path=to_vinh_dien_image,
            vo_thi_sau_image_path=vo_thi_sau_image,
        )
    )

    with TestClient(app) as client:
        characters = client.get("/api/v1/characters")
        image = client.get("/api/v1/characters/vo_thi_sau/image")

    assert characters.status_code == 200
    profiles = {item["id"]: item for item in characters.json()}
    assert set(profiles) == {"to_vinh_dien", "vo_thi_sau"}
    assert profiles["vo_thi_sau"]["voice_id"] == "002"
    assert profiles["vo_thi_sau"]["image_id"] == "002"
    assert image.status_code == 200
    assert image.content == vo_thi_sau_image.read_bytes()


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
        assert payload["character_id"] == "to_vinh_dien"
        assert payload["answer"] == "Chú sinh năm 1924 tại Thanh Hóa."
        assert payload["video_url"] == f"/api/v1/jobs/{job_id}/video"

        video = client.get(payload["video_url"])
        assert video.status_code == 200
        assert video.headers["content-type"].startswith("video/mp4")
        assert video.content == b"fake-mp4"


def test_talk_rejects_unknown_character(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            storage_dir=tmp_path / "storage",
            frontend_dist_dir=tmp_path / "frontend",
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/talk",
            json={
                "session_id": "demo-session-001",
                "message": "Xin chào",
                "character_id": "khong_ton_tai",
            },
        )

    assert response.status_code == 404
    assert "chưa được hỗ trợ" in response.json()["detail"]


def test_delete_session_proxies_to_llm(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            storage_dir=tmp_path / "storage",
            frontend_dist_dir=tmp_path / "frontend",
        )
    )
    upstream = SessionDeleteUpstream()

    with TestClient(app) as client:
        app.state.clients = upstream
        response = client.delete(
            "/api/v1/characters/vo_thi_sau/sessions/demo-session-002"
        )

    assert response.status_code == 200
    assert response.json() == {
        "character_id": "vo_thi_sau",
        "session_id": "demo-session-002",
        "deleted": True,
    }
    assert upstream.deleted == ("vo_thi_sau", "demo-session-002")

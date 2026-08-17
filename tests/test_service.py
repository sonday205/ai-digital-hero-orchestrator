from pathlib import Path

import pytest

from app.config import Settings
from app.jobs import JobStore
from app.schemas import JobStatus
from app.service import OrchestratorService


class SuccessfulClients:
    def __init__(self) -> None:
        self.character_id: str | None = None
        self.voice_id: str | None = None
        self.image_id: str | None = None

    async def ask_llm(self, session_id: str, message: str, character_id: str | None = None):
        self.character_id = character_id
        return "Chú sinh năm 1924 tại Thanh Hóa.", "request-1"

    async def start_tts(self, text: str, voice_id: str | None = None):
        self.voice_id = voice_id
        return "tts-task-1"

    async def wait_for_tts(self, task_id: str):
        return "/dev/shm/audio/tts-task-1.wav"

    async def start_lipsync(self, audio_path: str, image_id: str | None = None):
        self.image_id = image_id
        return "lipsync-task-1", "a" * 32

    async def wait_for_lipsync(self, task_id: str):
        return {"status": "completed"}

    async def create_video_download_url(self, lipsync_job_id: str, task_id: str):
        return "http://lipsync/video"

    async def download_video(self, download_url: str, target: Path):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake-mp4")


@pytest.mark.asyncio
async def test_full_pipeline_completes(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path)
    jobs = JobStore()
    clients = SuccessfulClients()
    service = OrchestratorService(settings, clients, jobs)  # type: ignore[arg-type]

    job = await service.submit("demo-session-001", "Chú sinh năm bao nhiêu?")
    for _ in range(100):
        current = await jobs.get(job.job_id)
        if current and current.status in {JobStatus.COMPLETED, JobStatus.FAILED}:
            break
        await __import__("asyncio").sleep(0.01)

    current = await jobs.get(job.job_id)
    assert current is not None
    assert current.status == JobStatus.COMPLETED
    assert current.answer == "Chú sinh năm 1924 tại Thanh Hóa."
    assert current.video_path is not None and current.video_path.is_file()
    await service.close()


@pytest.mark.asyncio
async def test_le_loi_pipeline_uses_character_voice_and_image_014(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path)
    jobs = JobStore()
    clients = SuccessfulClients()
    service = OrchestratorService(settings, clients, jobs)  # type: ignore[arg-type]

    job = await service.submit(
        "demo-session-014",
        "Khởi nghĩa Lam Sơn diễn ra như thế nào?",
        "le_loi",
    )
    for _ in range(100):
        current = await jobs.get(job.job_id)
        if current and current.status in {JobStatus.COMPLETED, JobStatus.FAILED}:
            break
        await __import__("asyncio").sleep(0.01)

    current = await jobs.get(job.job_id)
    assert current is not None
    assert current.status == JobStatus.COMPLETED
    assert current.character_id == "le_loi"
    assert clients.character_id == "le_loi"
    assert clients.voice_id == "014"
    assert clients.image_id == "014"
    await service.close()

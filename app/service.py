from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.clients import UpstreamClients, UpstreamServiceError
from app.config import Settings
from app.jobs import JobStore, OrchestrationJob
from app.schemas import JobStage


logger = logging.getLogger(__name__)


class OrchestratorService:
    def __init__(self, settings: Settings, clients: UpstreamClients, jobs: JobStore) -> None:
        self.settings = settings
        self.clients = clients
        self.jobs = jobs
        self._tasks: set[asyncio.Task[None]] = set()

    async def submit(
        self,
        session_id: str,
        message: str,
        character_id: str | None = None,
    ) -> OrchestrationJob:
        resolved_character_id = character_id or self.settings.character_id
        # Validate trước khi tạo background task để API có thể báo lỗi ngay.
        self.settings.get_character(resolved_character_id)
        job = await self.jobs.create(session_id, message, resolved_character_id)
        task = asyncio.create_task(self._run(job.job_id), name=f"orchestration-{job.job_id}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job

    async def close(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _run(self, job_id: str) -> None:
        job = await self.jobs.get(job_id)
        if job is None:
            return
        try:
            character = self.settings.get_character(job.character_id)
            await self.jobs.update_stage(job_id, JobStage.ASKING_LLM)
            answer, request_id = await self.clients.ask_llm(
                job.session_id,
                job.message,
                character.id,
            )
            await self.jobs.save_answer(job_id, answer, request_id)

            await self.jobs.update_stage(job_id, JobStage.GENERATING_VOICE)
            tts_task_id = await self.clients.start_tts(answer, character.voice_id)
            await self.jobs.save_tts_task(job_id, tts_task_id)
            audio_path = await self.clients.wait_for_tts(tts_task_id)

            await self.jobs.update_stage(job_id, JobStage.GENERATING_VIDEO)
            lipsync_task_id, lipsync_job_id = await self.clients.start_lipsync(
                audio_path,
                character.image_id,
            )
            await self.jobs.save_lipsync_task(job_id, lipsync_task_id, lipsync_job_id)
            await self.clients.wait_for_lipsync(lipsync_task_id)

            await self.jobs.update_stage(job_id, JobStage.DOWNLOADING_VIDEO)
            download_url = await self.clients.create_video_download_url(
                lipsync_job_id,
                lipsync_task_id,
            )
            video_path = self._video_path(job_id)
            await self.clients.download_video(download_url, video_path)
            await self.jobs.complete(job_id, video_path)
        except asyncio.CancelledError:
            await self.jobs.fail(job_id, "Orchestrator đã dừng khi yêu cầu đang được xử lý.")
            raise
        except UpstreamServiceError as exc:
            logger.warning("Orchestration failed job=%s service=%s", job_id, exc.service)
            await self.jobs.fail(job_id, exc.public_message)
        except Exception:
            logger.exception("Unexpected orchestration error job=%s", job_id)
            await self.jobs.fail(job_id, "Đã xảy ra lỗi ngoài dự kiến khi tạo video.")

    def _video_path(self, job_id: str) -> Path:
        return self.settings.storage_dir / "jobs" / job_id / "result.mp4"

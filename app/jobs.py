from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.schemas import JobResponse, JobStage, JobStatus, STAGE_LABELS


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class OrchestrationJob:
    session_id: str
    message: str
    job_id: str = field(default_factory=lambda: uuid4().hex)
    status: JobStatus = JobStatus.QUEUED
    stage: JobStage = JobStage.QUEUED
    answer: str | None = None
    video_path: Path | None = None
    error: str | None = None
    llm_request_id: str | None = None
    tts_task_id: str | None = None
    lipsync_task_id: str | None = None
    lipsync_job_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None

    def to_response(self) -> JobResponse:
        # Theo yêu cầu UX, câu trả lời chỉ được công bố khi toàn bộ video đã xong.
        is_completed = self.status == JobStatus.COMPLETED
        return JobResponse(
            job_id=self.job_id,
            status=self.status,
            stage=self.stage,
            stage_label=STAGE_LABELS[self.stage],
            message=self.message,
            answer=self.answer if is_completed else None,
            video_url=f"/api/v1/jobs/{self.job_id}/video" if is_completed else None,
            error=self.error,
            created_at=self.created_at,
            updated_at=self.updated_at,
            completed_at=self.completed_at,
        )


class JobStore:
    """Job store in-memory cho bản demo một instance."""

    def __init__(self) -> None:
        self._jobs: dict[str, OrchestrationJob] = {}
        self._lock = asyncio.Lock()

    async def create(self, session_id: str, message: str) -> OrchestrationJob:
        job = OrchestrationJob(session_id=session_id, message=message)
        async with self._lock:
            self._jobs[job.job_id] = job
        return job

    async def get(self, job_id: str) -> OrchestrationJob | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def update_stage(self, job_id: str, stage: JobStage) -> None:
        async with self._lock:
            job = self._require(job_id)
            job.status = JobStatus.PROCESSING
            job.stage = stage
            job.updated_at = utc_now()

    async def save_answer(self, job_id: str, answer: str, request_id: str | None) -> None:
        async with self._lock:
            job = self._require(job_id)
            job.answer = answer
            job.llm_request_id = request_id
            job.updated_at = utc_now()

    async def save_tts_task(self, job_id: str, task_id: str) -> None:
        async with self._lock:
            job = self._require(job_id)
            job.tts_task_id = task_id
            job.updated_at = utc_now()

    async def save_lipsync_task(self, job_id: str, task_id: str, lipsync_job_id: str) -> None:
        async with self._lock:
            job = self._require(job_id)
            job.lipsync_task_id = task_id
            job.lipsync_job_id = lipsync_job_id
            job.updated_at = utc_now()

    async def complete(self, job_id: str, video_path: Path) -> None:
        async with self._lock:
            job = self._require(job_id)
            completed_at = utc_now()
            job.video_path = video_path
            job.status = JobStatus.COMPLETED
            job.stage = JobStage.COMPLETED
            job.completed_at = completed_at
            job.updated_at = completed_at

    async def fail(self, job_id: str, message: str) -> None:
        async with self._lock:
            job = self._require(job_id)
            job.status = JobStatus.FAILED
            job.stage = JobStage.FAILED
            job.error = message
            job.updated_at = utc_now()

    def _require(self, job_id: str) -> OrchestrationJob:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise LookupError(job_id) from exc

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStage(StrEnum):
    QUEUED = "queued"
    ASKING_LLM = "asking_llm"
    GENERATING_VOICE = "generating_voice"
    GENERATING_VIDEO = "generating_video"
    DOWNLOADING_VIDEO = "downloading_video"
    COMPLETED = "completed"
    FAILED = "failed"


STAGE_LABELS: dict[JobStage, str] = {
    JobStage.QUEUED: "Đang xếp yêu cầu vào hàng đợi",
    JobStage.ASKING_LLM: "Đang trò chuyện cùng nhân vật",
    JobStage.GENERATING_VOICE: "Đang tạo giọng nói",
    JobStage.GENERATING_VIDEO: "Đang tạo chuyển động khuôn mặt",
    JobStage.DOWNLOADING_VIDEO: "Đang hoàn thiện video",
    JobStage.COMPLETED: "Đã hoàn thành",
    JobStage.FAILED: "Không thể hoàn thành",
}


class TalkRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=120)
    message: str = Field(min_length=1, max_length=2000)


class TalkAccepted(BaseModel):
    job_id: str
    status: Literal["queued"] = "queued"
    status_url: str


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    stage: JobStage
    stage_label: str
    message: str
    answer: str | None = None
    video_url: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    port: int


class UpstreamState(BaseModel):
    name: str
    reachable: bool
    url: str
    status_code: int | None = None
    detail: str | None = None
    payload: dict[str, Any] | None = None


class UpstreamsHealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    services: list[UpstreamState]

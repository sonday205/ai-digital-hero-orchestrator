from pathlib import Path

import pytest

from app.jobs import JobStore
from app.schemas import JobStage, JobStatus


@pytest.mark.asyncio
async def test_answer_is_hidden_until_video_is_complete(tmp_path: Path) -> None:
    store = JobStore()
    job = await store.create("demo-session-001", "Chú sinh năm bao nhiêu?")

    await store.update_stage(job.job_id, JobStage.GENERATING_VOICE)
    await store.save_answer(job.job_id, "Chú sinh năm 1924.", "llm-request-1")
    processing = (await store.get(job.job_id)).to_response()  # type: ignore[union-attr]

    assert processing.status == JobStatus.PROCESSING
    assert processing.character_id == "to_vinh_dien"
    assert processing.answer is None
    assert processing.video_url is None

    video_path = tmp_path / "result.mp4"
    video_path.write_bytes(b"video")
    await store.complete(job.job_id, video_path)
    completed = (await store.get(job.job_id)).to_response()  # type: ignore[union-attr]

    assert completed.answer == "Chú sinh năm 1924."
    assert completed.video_url == f"/api/v1/jobs/{job.job_id}/video"

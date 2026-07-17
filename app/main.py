from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.clients import UpstreamClients
from app.config import Settings, get_settings
from app.jobs import JobStore
from app.schemas import (
    HealthResponse,
    JobResponse,
    JobStatus,
    TalkAccepted,
    TalkRequest,
    UpstreamsHealthResponse,
)
from app.service import OrchestratorService
from app.voice import proxy_voice


logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    logging.basicConfig(
        level=getattr(logging, resolved.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved.storage_dir.mkdir(parents=True, exist_ok=True)
        http = httpx.AsyncClient(follow_redirects=True, limits=httpx.Limits(max_connections=40))
        clients = UpstreamClients(resolved, http)
        jobs = JobStore()
        orchestrator = OrchestratorService(resolved, clients, jobs)
        app.state.settings = resolved
        app.state.clients = clients
        app.state.jobs = jobs
        app.state.orchestrator = orchestrator
        try:
            yield
        finally:
            await orchestrator.close()
            await http.aclose()

    app = FastAPI(
        title="AI Digital Hero Orchestrator",
        version="1.0.0",
        description="Điều phối LLM, OmniVoice TTS và SoulX LipSync cho nhân vật Tô Vĩnh Diện.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(service=resolved.app_name, port=resolved.app_port)

    @app.get(
        "/api/health/upstreams",
        response_model=UpstreamsHealthResponse,
        tags=["health"],
    )
    async def upstream_health(request: Request) -> UpstreamsHealthResponse:
        services = await request.app.state.clients.health()
        return UpstreamsHealthResponse(
            status="ok" if all(item.reachable for item in services) else "degraded",
            services=services,
        )

    @app.post(
        "/api/v1/talk",
        response_model=TalkAccepted,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["conversation"],
    )
    async def talk(payload: TalkRequest, request: Request) -> TalkAccepted:
        job = await request.app.state.orchestrator.submit(
            payload.session_id,
            payload.message.strip(),
        )
        return TalkAccepted(job_id=job.job_id, status_url=f"/api/v1/jobs/{job.job_id}")

    @app.get(
        "/api/v1/jobs/{job_id}",
        response_model=JobResponse,
        tags=["conversation"],
    )
    async def get_job(job_id: str, request: Request) -> JobResponse:
        job = await request.app.state.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy orchestration job.")
        return job.to_response()

    @app.get("/api/v1/jobs/{job_id}/video", tags=["conversation"])
    async def get_video(job_id: str, request: Request) -> FileResponse:
        job = await request.app.state.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy orchestration job.")
        if job.status != JobStatus.COMPLETED or job.video_path is None:
            raise HTTPException(status_code=409, detail="Video chưa hoàn thành.")
        if not job.video_path.is_file():
            raise HTTPException(status_code=404, detail="Không tìm thấy file video.")
        return FileResponse(
            job.video_path,
            media_type="video/mp4",
            headers={"Cache-Control": "private, no-store"},
        )

    @app.get("/api/v1/character/image", tags=["character"])
    async def character_image() -> FileResponse:
        path = resolved.character_image_path
        if not path.is_file():
            path = Path(__file__).resolve().parents[1] / "assets" / "001.svg"
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Chưa cấu hình ảnh nhân vật.")
        return FileResponse(
            path,
            media_type=_detect_image_media_type(path),
            headers={"Cache-Control": "public, max-age=300"},
        )

    @app.websocket("/api/v1/voice/{character_id}")
    async def voice(websocket: WebSocket, character_id: str) -> None:
        await proxy_voice(websocket, character_id, resolved)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    static_dir = resolved.frontend_dist_dir
    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def frontend(full_path: str):
        index = static_dir / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Frontend chưa được build. Chạy `npm run build` trong thư mục frontend."
            },
        )

    return app


def _detect_image_media_type(path: Path) -> str:
    with path.open("rb") as image:
        header = image.read(16)
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if b"<svg" in header.lower() or path.suffix.lower() == ".svg":
        return "image/svg+xml"
    return "application/octet-stream"


app = create_app()

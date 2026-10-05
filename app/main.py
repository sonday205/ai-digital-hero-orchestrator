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
    CharacterSummary,
    HealthResponse,
    JobResponse,
    JobStatus,
    SessionDeleteResponse,
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
        version="1.1.0",
        description="Điều phối LLM, OmniVoice TTS và SoulX LipSync cho các nhân vật lịch sử.",
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

    @app.get(
        "/api/v1/characters",
        response_model=list[CharacterSummary],
        tags=["character"],
    )
    async def list_characters() -> list[CharacterSummary]:
        return [
            CharacterSummary(
                id=character.id,
                display_name=character.display_name,
                self_pronoun=character.self_pronoun,
                student_pronoun=character.student_pronoun,
                short_description=character.short_description,
                title=character.title,
                life_years=character.life_years,
                era_label=character.era_label,
                quote=character.quote,
                greeting=character.greeting,
                voice_id=character.voice_id,
                image_id=character.image_id,
                image_url=f"/api/v1/characters/{character.id}/image",
            )
            for character in resolved.characters
        ]

    @app.delete(
        "/api/v1/characters/{character_id}/sessions/{session_id}",
        response_model=SessionDeleteResponse,
        tags=["conversation"],
    )
    async def delete_session(
        character_id: str,
        session_id: str,
        request: Request,
    ) -> SessionDeleteResponse:
        try:
            resolved.get_character(character_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        deleted = await request.app.state.clients.delete_llm_session(
            character_id,
            session_id,
        )
        return SessionDeleteResponse(
            character_id=character_id,
            session_id=session_id,
            deleted=deleted,
        )

    @app.post(
        "/api/v1/talk",
        response_model=TalkAccepted,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["conversation"],
    )
    async def talk(payload: TalkRequest, request: Request) -> TalkAccepted:
        try:
            job = await request.app.state.orchestrator.submit(
                payload.session_id,
                payload.message.strip(),
                payload.character_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return TalkAccepted(
            job_id=job.job_id,
            character_id=job.character_id,
            status_url=f"/api/v1/jobs/{job.job_id}",
        )

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

    def character_image_response(character_id: str) -> FileResponse:
        try:
            character = resolved.get_character(character_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        path = character.image_path.expanduser()
        if not path.is_file() and not path.suffix:
            for extension in (".jpg", ".jpeg", ".png", ".svg"):
                candidate = path.with_suffix(extension)
                if candidate.is_file():
                    path = candidate
                    break
        if not path.is_file():
            path = Path(__file__).resolve().parents[1] / "assets" / f"{character.image_id}.svg"
        if not path.is_file():
            path = Path(__file__).resolve().parents[1] / "assets" / "placeholder.svg"
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Chưa cấu hình ảnh nhân vật.")
        return FileResponse(
            path,
            media_type=_detect_image_media_type(path),
            # Ảnh có thể được thay bằng file khác trong lúc triển khai. Không cache
            # để frontend phản ánh ngay CHARACTER_IMAGE_PATH mới.
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/v1/characters/{character_id}/image", tags=["character"])
    async def character_image(character_id: str) -> FileResponse:
        return character_image_response(character_id)

    @app.get("/api/v1/character/image", tags=["character"], deprecated=True)
    async def legacy_character_image() -> FileResponse:
        """Endpoint cũ vẫn phục vụ ảnh của nhân vật mặc định."""

        return character_image_response(resolved.character_id)

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

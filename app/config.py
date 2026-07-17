from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Cấu hình adapter giữa orchestrator và ba API độc lập."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "digital-hero-orchestrator"
    app_host: str = "0.0.0.0"
    app_port: int = 8991
    log_level: str = "INFO"

    llm_base_url: str = "http://127.0.0.1:8005"
    llm_ws_base_url: str = "ws://127.0.0.1:8005"
    tts_base_url: str = "http://127.0.0.1:8989"
    lipsync_base_url: str = "http://127.0.0.1:8071"

    character_id: str = "to_vinh_dien"
    voice_id: str = "001"
    image_id: str = "001"

    llm_timeout_seconds: float = 45.0
    tts_timeout_seconds: float = 900.0
    lipsync_timeout_seconds: float = 3600.0
    video_download_timeout_seconds: float = 300.0
    poll_interval_seconds: float = Field(default=2.0, ge=0.1)
    voice_connect_timeout_seconds: float = 15.0

    storage_dir: Path = PROJECT_ROOT / "storage"
    frontend_dist_dir: Path = PROJECT_ROOT / "frontend" / "dist"
    character_image_path: Path = PROJECT_ROOT / "assets" / "001.svg"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

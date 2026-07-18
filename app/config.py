from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class CharacterConfig:
    """Mapping một nhân vật tới đúng LLM, giọng TTS và ảnh LipSync."""

    id: str
    display_name: str
    self_pronoun: str
    student_pronoun: str
    short_description: str
    title: str
    life_years: str
    era_label: str
    quote: str
    greeting: str
    voice_id: str
    image_id: str
    image_path: Path


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
    lipsync_base_url: str = "http://127.0.0.1:8990"

    character_id: str = "to_vinh_dien"
    voice_id: str = "001"
    image_id: str = "001"
    vo_thi_sau_voice_id: str = "002"
    vo_thi_sau_image_id: str = "002"

    llm_timeout_seconds: float = 45.0
    tts_timeout_seconds: float = 900.0
    lipsync_timeout_seconds: float = 3600.0
    video_download_timeout_seconds: float = 300.0
    poll_interval_seconds: float = Field(default=2.0, ge=0.1)
    voice_connect_timeout_seconds: float = 15.0

    storage_dir: Path = PROJECT_ROOT / "storage"
    frontend_dist_dir: Path = PROJECT_ROOT / "frontend" / "dist"
    character_image_path: Path = PROJECT_ROOT / "assets" / "001.svg"
    vo_thi_sau_image_path: Path = PROJECT_ROOT / "assets" / "002.svg"

    @property
    def characters(self) -> tuple[CharacterConfig, ...]:
        """Danh sách nhân vật public của orchestrator.

        Ba ID kỹ thuật phải luôn đi cùng nhau:
        character id của LLM, voice id của TTS và image id của LipSync.
        """

        return (
            CharacterConfig(
                id="to_vinh_dien",
                display_name="Tô Vĩnh Diện",
                self_pronoun="chú",
                student_pronoun="cháu",
                short_description="Anh hùng pháo binh trong Chiến dịch Điện Biên Phủ.",
                title="ANH HÙNG LIỆT SĨ",
                life_years="1924 — 1954",
                era_label="ĐIỆN BIÊN PHỦ · 1954",
                quote="Thà hy sinh, quyết bảo vệ pháo",
                greeting=(
                    "Chào cháu. Chú là Tô Vĩnh Diện. "
                    "Cháu muốn cùng chú tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.voice_id,
                image_id=self.image_id,
                image_path=self.character_image_path,
            ),
            CharacterConfig(
                id="vo_thi_sau",
                display_name="Võ Thị Sáu",
                self_pronoun="chị",
                student_pronoun="em",
                short_description="Người con gái Đất Đỏ kiên cường trong kháng chiến chống Pháp.",
                title="NỮ ANH HÙNG LIỆT SĨ",
                life_years="1933 — 1952",
                era_label="ĐẤT ĐỎ · CÔN ĐẢO",
                quote="Tinh thần kiên định, không khuất phục",
                greeting=(
                    "Chào em. Chị là Võ Thị Sáu. "
                    "Em muốn cùng chị tìm hiểu điều gì về lịch sử?"
                ),
                voice_id=self.vo_thi_sau_voice_id,
                image_id=self.vo_thi_sau_image_id,
                image_path=self.vo_thi_sau_image_path,
            ),
        )

    def get_character(self, character_id: str) -> CharacterConfig:
        for character in self.characters:
            if character.id == character_id:
                return character
        raise ValueError(f"Nhân vật chưa được hỗ trợ: {character_id}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

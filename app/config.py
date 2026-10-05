from __future__ import annotations

import json
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
    llm_api_key: str | None = None
    tts_base_url: str = "http://127.0.0.1:8989"
    lipsync_base_url: str = "http://127.0.0.1:8990"

    character_id: str = "to_vinh_dien"
    voice_id: str = "001"
    image_id: str = "001"
    vo_thi_sau_voice_id: str = "002"
    vo_thi_sau_image_id: str = "002"
    kim_dong_voice_id: str = "003"
    kim_dong_image_id: str = "003"
    le_van_tam_voice_id: str = "004"
    le_van_tam_image_id: str = "004"
    nguyen_van_troi_voice_id: str = "005"
    nguyen_van_troi_image_id: str = "005"
    le_hong_phong_voice_id: str = "006"
    le_hong_phong_image_id: str = "006"
    nguyen_binh_khiem_voice_id: str = "007"
    nguyen_binh_khiem_image_id: str = "007"
    nguyen_ba_ngoc_voice_id: str = "008"
    nguyen_ba_ngoc_image_id: str = "008"
    le_chan_voice_id: str = "009"
    le_chan_image_id: str = "009"
    le_ngoc_han_voice_id: str = "010"
    le_ngoc_han_image_id: str = "010"
    dinh_nup_voice_id: str = "011"
    dinh_nup_image_id: str = "011"
    ngo_quyen_voice_id: str = "012"
    ngo_quyen_image_id: str = "012"
    quang_trung_nguyen_hue_voice_id: str = "013"
    quang_trung_nguyen_hue_image_id: str = "013"
    le_loi_voice_id: str = "014"
    le_loi_image_id: str = "014"

    llm_timeout_seconds: float = 45.0
    tts_timeout_seconds: float = 900.0
    lipsync_timeout_seconds: float = 3600.0
    video_download_timeout_seconds: float = 300.0
    poll_interval_seconds: float = Field(default=2.0, ge=0.1)
    voice_connect_timeout_seconds: float = 15.0

    @property
    def llm_headers(self) -> dict[str, str]:
        """Header server-to-server; không đưa application key xuống browser."""

        key = (self.llm_api_key or "").strip()
        return {"X-API-Key": key} if key else {}

    storage_dir: Path = PROJECT_ROOT / "storage"
    frontend_dist_dir: Path = PROJECT_ROOT / "frontend" / "dist"
    character_image_path: Path = PROJECT_ROOT / "assets" / "001.svg"
    vo_thi_sau_image_path: Path = PROJECT_ROOT / "assets" / "002.svg"
    kim_dong_image_path: Path = PROJECT_ROOT / "assets" / "003.svg"
    le_van_tam_image_path: Path = PROJECT_ROOT / "assets" / "004.svg"
    nguyen_van_troi_image_path: Path = PROJECT_ROOT / "assets" / "005.svg"
    le_hong_phong_image_path: Path = PROJECT_ROOT / "assets" / "006.svg"
    nguyen_binh_khiem_image_path: Path = PROJECT_ROOT / "assets" / "007.svg"
    nguyen_ba_ngoc_image_path: Path = PROJECT_ROOT / "assets" / "008.svg"
    le_chan_image_path: Path = PROJECT_ROOT / "assets" / "009.svg"
    le_ngoc_han_image_path: Path = PROJECT_ROOT / "assets" / "010.svg"
    dinh_nup_image_path: Path = PROJECT_ROOT / "assets" / "011.svg"
    ngo_quyen_image_path: Path = PROJECT_ROOT / "assets" / "012.svg"
    quang_trung_nguyen_hue_image_path: Path = PROJECT_ROOT / "assets" / "013.svg"
    le_loi_image_path: Path = PROJECT_ROOT / "assets" / "014.svg"

    character_catalog_path: Path = PROJECT_ROOT / "data" / "characters.json"
    portrait_dir: Path = PROJECT_ROOT / "assets"
    character_overrides_json: str = "{}"

    @property
    def characters(self) -> tuple[CharacterConfig, ...]:
        """Đọc catalog chung; giữ các biến môi trường cũ và hỗ trợ override mọi ID."""
        catalog = json.loads(self.character_catalog_path.read_text(encoding="utf-8"))
        overrides = json.loads(self.character_overrides_json or "{}")
        if not isinstance(catalog, list) or not isinstance(overrides, dict):
            raise ValueError("Character catalog phải là list; overrides phải là object")
        ids = [item["id"] for item in catalog]
        if len(ids) != len(set(ids)):
            raise ValueError("Character catalog có ID trùng")
        if set(overrides) - set(ids):
            raise ValueError("Character overrides chứa ID không có trong catalog")

        characters = []
        for item in catalog:
            override = overrides.get(item["id"], {})
            if not isinstance(override, dict) or set(override) - {
                "voice_id",
                "image_id",
                "image_path",
            }:
                raise ValueError("Override chỉ hỗ trợ voice_id, image_id, image_path")
            if any(
                not isinstance(value, str) or not value.strip()
                for value in override.values()
            ):
                raise ValueError("Giá trị override phải là chuỗi không rỗng")
            prefix = "" if item["id"] == "to_vinh_dien" else f"{item['id']}_"
            voice_id = override.get(
                "voice_id", getattr(self, f"{prefix}voice_id", item["voice_id"])
            )
            image_id = override.get(
                "image_id", getattr(self, f"{prefix}image_id", item["image_id"])
            )
            image_setting = (
                "character_image_path" if not prefix else f"{prefix}image_path"
            )
            image_path = getattr(self, image_setting, self.portrait_dir / image_id)
            metadata = {
                key: value
                for key, value in item.items()
                if key not in {"voice_id", "image_id"}
            }
            characters.append(
                CharacterConfig(
                    **metadata,
                    voice_id=voice_id,
                    image_id=image_id,
                    image_path=Path(override.get("image_path", str(image_path))),
                )
            )
        return tuple(characters)

    def get_character(self, character_id: str) -> CharacterConfig:
        for character in self.characters:
            if character.id == character_id:
                return character
        raise ValueError(f"Nhân vật chưa được hỗ trợ: {character_id}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

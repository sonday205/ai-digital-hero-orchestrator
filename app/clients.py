from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import httpx

from app.config import Settings
from app.schemas import UpstreamState


class UpstreamServiceError(RuntimeError):
    def __init__(self, service: str, message: str) -> None:
        self.service = service
        self.public_message = message
        super().__init__(f"{service}: {message}")


class UpstreamClients:
    """HTTP adapter duy nhất tới LLM, TTS và LipSync."""

    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self.settings = settings
        self.http = http

    async def ask_llm(
        self,
        session_id: str,
        message: str,
        character_id: str | None = None,
    ) -> tuple[str, str | None]:
        resolved_character_id = character_id or self.settings.character_id
        data = await self._json_request(
            "llm",
            "POST",
            f"{self.settings.llm_base_url}/v1/characters/{resolved_character_id}/chat",
            timeout=self.settings.llm_timeout_seconds,
            headers=self.settings.llm_headers,
            json={"session_id": session_id, "message": message, "debug": False},
        )
        answer = str(data.get("answer") or "").strip()
        if not answer:
            raise UpstreamServiceError("LLM", "LLM không trả về câu trả lời.")
        return answer, self._optional_text(data.get("request_id"))

    async def delete_llm_session(self, character_id: str, session_id: str) -> bool:
        """Xóa memory của một phiên tại LLM trước khi frontend quên phiên đó."""

        encoded_character_id = quote(character_id, safe="")
        encoded_session_id = quote(session_id, safe="")
        data = await self._json_request(
            "llm",
            "DELETE",
            (
                f"{self.settings.llm_base_url}/v1/characters/"
                f"{encoded_character_id}/sessions/{encoded_session_id}"
            ),
            timeout=self.settings.llm_timeout_seconds,
            headers=self.settings.llm_headers,
        )
        return bool(data.get("deleted"))

    async def start_tts(self, text: str, voice_id: str | None = None) -> str:
        data = await self._json_request(
            "tts",
            "POST",
            f"{self.settings.tts_base_url}/api/v1/tts/generate",
            timeout=30.0,
            json={
                "text": text,
                "voice_id": voice_id or self.settings.voice_id,
                "speed": 1.0,
                "stream": False,
            },
        )
        task_id = self._optional_text(data.get("task_id"))
        if not task_id:
            raise UpstreamServiceError("TTS", "TTS không trả về task_id.")
        return task_id

    async def wait_for_tts(self, task_id: str) -> str:
        deadline = time.monotonic() + self.settings.tts_timeout_seconds
        while time.monotonic() < deadline:
            data = await self._json_request(
                "tts",
                "GET",
                f"{self.settings.tts_base_url}/api/v1/tts/status/{task_id}",
                timeout=20.0,
            )
            status = str(data.get("status") or "").strip().lower()
            if status in {"success", "completed", "complete"}:
                audio_path = self._optional_text(data.get("audio_path"))
                if audio_path:
                    return audio_path
                detail = self._optional_text(data.get("message")) or "TTS hoàn thành nhưng thiếu audio_path."
                raise UpstreamServiceError("TTS", detail)
            if status in {"error", "failed", "failure", "revoked"}:
                detail = self._optional_text(data.get("message")) or "Không thể tạo giọng nói."
                raise UpstreamServiceError("TTS", detail)
            await asyncio.sleep(self.settings.poll_interval_seconds)
        raise UpstreamServiceError("TTS", "Quá thời gian chờ tạo giọng nói.")

    async def start_lipsync(
        self,
        audio_path: str,
        image_id: str | None = None,
    ) -> tuple[str, str]:
        data = await self._json_request(
            "lipsync",
            "POST",
            f"{self.settings.lipsync_base_url}/api/v1/lipsync/generate",
            timeout=30.0,
            json={"image_id": image_id or self.settings.image_id, "audio_path": audio_path},
        )
        task_id = self._optional_text(data.get("task_id"))
        job_id = self._optional_text(data.get("job_id"))
        if not task_id or not job_id:
            raise UpstreamServiceError("LipSync", "LipSync không trả về task_id/job_id.")
        return task_id, job_id

    async def wait_for_lipsync(self, task_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.settings.lipsync_timeout_seconds
        while time.monotonic() < deadline:
            data = await self._json_request(
                "lipsync",
                "GET",
                f"{self.settings.lipsync_base_url}/api/v1/lipsync/tasks/{task_id}",
                timeout=20.0,
            )
            state = str(data.get("state") or "").strip().upper()
            meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
            meta_status = str(meta.get("status") or "").strip().lower()

            if state == "SUCCESS":
                if meta_status and meta_status != "completed":
                    detail = self._optional_text(meta.get("error")) or "LipSync không hoàn thành video."
                    raise UpstreamServiceError("LipSync", detail)
                return meta
            if state in {"FAILURE", "REVOKED"} or meta_status == "failed":
                detail = self._optional_text(meta.get("error")) or "Không thể tạo video LipSync."
                raise UpstreamServiceError("LipSync", detail)
            await asyncio.sleep(self.settings.poll_interval_seconds)
        raise UpstreamServiceError("LipSync", "Quá thời gian chờ tạo video.")

    async def create_video_download_url(self, lipsync_job_id: str, task_id: str) -> str:
        data = await self._json_request(
            "lipsync",
            "POST",
            f"{self.settings.lipsync_base_url}/api/v1/lipsync/jobs/{lipsync_job_id}/download-url",
            timeout=30.0,
            params={"task_id": task_id},
        )
        download_url = self._optional_text(data.get("download_url"))
        if not download_url:
            raise UpstreamServiceError("LipSync", "LipSync không cấp URL tải video.")
        return self._route_download_through_configured_host(download_url)

    async def download_video(self, download_url: str, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(".part")
        try:
            timeout = httpx.Timeout(self.settings.video_download_timeout_seconds)
            async with self.http.stream("GET", download_url, timeout=timeout) as response:
                response.raise_for_status()
                with partial.open("wb") as output:
                    async for chunk in response.aiter_bytes():
                        output.write(chunk)
            if not partial.is_file() or partial.stat().st_size == 0:
                raise UpstreamServiceError("LipSync", "Video tải về bị rỗng.")
            partial.replace(target)
        except UpstreamServiceError:
            partial.unlink(missing_ok=True)
            raise
        except (httpx.HTTPError, OSError) as exc:
            partial.unlink(missing_ok=True)
            raise UpstreamServiceError("LipSync", "Không thể tải video đã tạo.") from exc

    async def health(self) -> list[UpstreamState]:
        checks = (
            ("LLM", self.settings.llm_base_url, "/health"),
            ("TTS", self.settings.tts_base_url, "/api/v1/health/"),
            ("LipSync", self.settings.lipsync_base_url, "/health"),
        )
        return await asyncio.gather(*(self._health_one(*check) for check in checks))

    async def _health_one(self, name: str, base_url: str, path: str) -> UpstreamState:
        url = f"{base_url}{path}"
        try:
            response = await self.http.get(url, timeout=5.0)
            payload = response.json() if response.content else None
            return UpstreamState(
                name=name,
                reachable=response.status_code < 500,
                url=url,
                status_code=response.status_code,
                payload=payload if isinstance(payload, dict) else None,
                detail=None if response.status_code < 400 else "Upstream trả trạng thái chưa sẵn sàng.",
            )
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
            return UpstreamState(name=name, reachable=False, url=url, detail=type(exc).__name__)

    async def _json_request(
        self,
        service: str,
        method: str,
        url: str,
        *,
        timeout: float,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            response = await self.http.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            raise UpstreamServiceError(service, f"{service} phản hồi quá chậm.") from exc
        except httpx.HTTPStatusError as exc:
            detail = self._response_detail(exc.response)
            raise UpstreamServiceError(service, detail) from exc
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
            raise UpstreamServiceError(service, f"Không kết nối được tới {service}.") from exc
        if not isinstance(data, dict):
            raise UpstreamServiceError(service, f"{service} trả dữ liệu không đúng định dạng.")
        return data

    def _route_download_through_configured_host(self, download_url: str) -> str:
        """Giữ path/chữ ký nhưng dùng host LipSync mà orchestrator chắc chắn truy cập được."""
        parsed = urlsplit(download_url)
        if not parsed.path.startswith("/api/v1/lipsync/"):
            return download_url
        base = urlsplit(self.settings.lipsync_base_url)
        return urlunsplit((base.scheme, base.netloc, parsed.path, parsed.query, ""))

    @staticmethod
    def _response_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict) and payload.get("detail"):
                return str(payload["detail"])
        except ValueError:
            pass
        return f"Upstream trả HTTP {response.status_code}."

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

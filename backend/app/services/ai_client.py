from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from backend.app.core.config import settings


class AIClient:
    def __init__(self, base_url: str | None = None, timeout: float = 120.0) -> None:
        self.base_url = (base_url or settings.ai_layer_url).rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        detail: Any
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise HTTPException(status_code=response.status_code, detail=detail)

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(method, self._url(path), **kwargs)
        except httpx.ConnectError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"AI layer unreachable at {self.base_url}. Start it with: python start.py ai",
            ) from exc
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="AI layer request timed out.") from exc
        self._raise_for_status(response)
        return response

    def health(self) -> dict[str, Any]:
        response = self._request("GET", "/health/ai", timeout=10.0)
        return response.json()

    def upload(
        self,
        *,
        filename: str | None = None,
        content: bytes | None = None,
        content_type: str | None = None,
        text: str | None = None,
    ) -> dict[str, Any]:
        files = None
        data: dict[str, str] = {}
        if content and filename:
            files = {"file": (filename, content, content_type or "application/octet-stream")}
        if text:
            data["text"] = text

        response = self._request("POST", "/api/ai/upload", files=files, data=data or None)
        return response.json()

    def restore_document(
        self,
        *,
        document_id: str,
        filename: str,
        detected_type: str,
        text: str,
    ) -> dict[str, Any]:
        payload = {
            "document_id": document_id,
            "filename": filename,
            "detected_type": detected_type,
            "text": text,
        }
        response = self._request("POST", "/api/ai/documents/restore", json=payload)
        return response.json()

    def delete_document(self, document_id: str) -> dict[str, Any]:
        response = self._request("DELETE", f"/api/ai/documents/{document_id}")
        return response.json()

    def summary(self, document_id: str) -> dict[str, Any]:
        response = self._request("GET", "/api/ai/summary", params={"document_id": document_id})
        return response.json()

    def keypoints(self, document_id: str) -> dict[str, Any]:
        response = self._request("GET", "/api/ai/keypoints", params={"document_id": document_id})
        return response.json()

    def topic_keypoints(self, document_id: str, *, topic: str) -> dict[str, Any]:
        response = self._request(
            "GET",
            "/api/ai/topic-keypoints",
            params={"document_id": document_id, "topic": topic},
        )
        return response.json()

    def notes(
        self,
        document_id: str,
        *,
        chapter_id: str,
        topic: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"document_id": document_id, "chapter_id": chapter_id}
        if topic:
            params["topic"] = topic
        response = self._request("GET", "/api/ai/notes", params=params)
        return response.json()

    def questions(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("POST", "/api/ai/questions", json=payload)
        return response.json()

    def review(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("POST", "/api/ai/review", json=payload)
        return response.json()

    def doubt(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("POST", "/api/ai/doubt", json=payload)
        return response.json()

    def start_doubt(self, document_id: str) -> dict[str, Any]:
        response = self._request("POST", "/api/ai/doubt/start", json={"document_id": document_id})
        return response.json()

    def chapters(self, document_id: str) -> dict[str, Any]:
        response = self._request("GET", f"/api/ai/documents/{document_id}/chapters")
        return response.json()

    def chunks(
        self,
        document_id: str,
        *,
        chapter_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if chapter_id:
            params["chapter_id"] = chapter_id
        response = self._request(
            "GET",
            f"/api/ai/documents/{document_id}/chunks",
            params=params,
        )
        return response.json()


ai_client = AIClient()

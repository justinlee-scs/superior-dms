from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class LabelStudioConfig:
    base_url: str
    api_token: str
    project_id: int
    timeout_seconds: int = 20


class LabelStudioClient:
    """Small client for Label Studio task import/export."""

    def __init__(self, config: LabelStudioConfig):
        self._config = config
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        self._auth_mode = self._resolve_auth_mode(config.api_token)
        self._access_token = ""
        self._apply_auth_header()

    @staticmethod
    def _parse_jwt_payload(token: str) -> dict[str, Any]:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1]
        padded = payload + "=" * (-len(payload) % 4)
        try:
            decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
            obj = json.loads(decoded)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    def _resolve_auth_mode(self, token: str) -> str:
        mode = os.getenv("LABEL_STUDIO_AUTH_MODE", "").strip().lower()
        if mode in {"pat", "legacy"}:
            return mode

        # Backward-compatible override.
        scheme = os.getenv("LABEL_STUDIO_AUTH_SCHEME", "").strip().lower()
        if scheme == "bearer":
            return "pat"
        if scheme == "token":
            return "legacy"

        payload = self._parse_jwt_payload(token)
        token_type = str(payload.get("token_type", "")).strip().lower()
        if token_type == "refresh":
            return "pat"
        return "legacy"

    def _refresh_access_token(self) -> str:
        url = f"{self._config.base_url}/api/token/refresh"
        response = self._session.post(
            url,
            json={"refresh": self._config.api_token},
            timeout=self._config.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        access = str((data or {}).get("access") or "").strip()
        if not access:
            raise RuntimeError("Label Studio PAT refresh succeeded but no access token was returned.")
        self._access_token = access
        return access

    def _apply_auth_header(self) -> None:
        if self._auth_mode == "pat":
            access = self._access_token or self._refresh_access_token()
            self._session.headers["Authorization"] = f"Bearer {access}"
            return
        self._session.headers["Authorization"] = f"Token {self._config.api_token}"

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        response = self._session.request(method=method, url=url, **kwargs)
        if response.status_code == 401 and self._auth_mode == "pat":
            # Access tokens are short-lived; refresh once and retry.
            self._access_token = ""
            self._apply_auth_header()
            response = self._session.request(method=method, url=url, **kwargs)
        response.raise_for_status()
        return response

    def import_tasks(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        url = f"{self._config.base_url}/api/projects/{self._config.project_id}/import"
        response = self._request(
            method="POST",
            url=url,
            json=tasks,
            timeout=self._config.timeout_seconds,
        )
        return response.json()

    def export_tasks(self, *, export_type: str = "JSON_MIN") -> list[dict[str, Any]]:
        url = (
            f"{self._config.base_url}/api/projects/{self._config.project_id}/export"
            f"?exportType={export_type}"
        )
        response = self._request("GET", url, timeout=self._config.timeout_seconds)
        data = response.json()
        if isinstance(data, list):
            return data
        return data.get("tasks", [])

    def create_task_for_document(self, *, doc_id: str, filename: str, text: str) -> dict[str, Any]:
        payload = [
            {
                "data": {
                    "document_id": doc_id,
                    "filename": filename,
                    "ocr_text": text,
                }
            }
        ]
        return self.import_tasks(payload)

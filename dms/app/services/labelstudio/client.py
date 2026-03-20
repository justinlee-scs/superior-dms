from __future__ import annotations

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
        auth_scheme = os.getenv("LABEL_STUDIO_AUTH_SCHEME", "Token").strip() or "Token"
        self._session.headers.update(
            {
                "Authorization": f"{auth_scheme} {config.api_token}",
                "Content-Type": "application/json",
            }
        )

    def import_tasks(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        url = f"{self._config.base_url}/api/projects/{self._config.project_id}/import"
        response = self._session.post(
            url,
            json=tasks,
            timeout=self._config.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def export_tasks(self, *, export_type: str = "JSON_MIN") -> list[dict[str, Any]]:
        url = (
            f"{self._config.base_url}/api/projects/{self._config.project_id}/export"
            f"?exportType={export_type}"
        )
        response = self._session.get(url, timeout=self._config.timeout_seconds)
        response.raise_for_status()
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

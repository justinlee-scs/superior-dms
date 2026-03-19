from __future__ import annotations

import argparse
import json
import os
from typing import Any

import requests


def export_tasks(base_url: str, api_token: str, project_id: int) -> list[dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/projects/{project_id}/export?exportType=JSON_MIN"
    headers = {"Authorization": f"Token {api_token}"}
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return data
    return data.get("tasks", [])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    base_url = os.getenv("LABEL_STUDIO_URL", "").strip()
    api_token = os.getenv("LABEL_STUDIO_API_TOKEN", "").strip()
    project_id = int(os.getenv("LABEL_STUDIO_PROJECT_ID", "0") or "0")

    if not base_url or not api_token or project_id <= 0:
        raise SystemExit("Set LABEL_STUDIO_URL, LABEL_STUDIO_API_TOKEN, LABEL_STUDIO_PROJECT_ID.")

    tasks = export_tasks(base_url=base_url, api_token=api_token, project_id=project_id)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(tasks)} tasks to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import requests


def _looks_like_pat(token: str) -> bool:
    # PATs are JWT refresh tokens; legacy tokens are usually opaque strings.
    return token.count(".") >= 2


def _refresh_pat(base_url: str, pat_token: str) -> str:
    refresh_url = f"{base_url.rstrip('/')}/api/token/refresh"
    refresh_response = requests.post(
        refresh_url,
        json={"refresh": pat_token},
        timeout=30,
    )
    refresh_response.raise_for_status()
    access_token = str((refresh_response.json() or {}).get("access") or "").strip()
    if not access_token:
        raise RuntimeError("PAT refresh did not return an access token.")
    return access_token


def _auth_headers(base_url: str, api_token: str) -> dict[str, str]:
    if _looks_like_pat(api_token):
        access_token = _refresh_pat(base_url=base_url, pat_token=api_token)
        return {"Authorization": f"Bearer {access_token}"}
    return {"Authorization": f"Token {api_token}"}


def _http_export_with_pat(base_url: str, pat_token: str, project_id: int) -> list[dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/projects/{project_id}/export?exportType=JSON_MIN"
    headers = _auth_headers(base_url=base_url, api_token=pat_token)
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return data
    return data.get("tasks", [])


def _http_export_with_legacy(base_url: str, api_token: str, project_id: int) -> list[dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/projects/{project_id}/export?exportType=JSON_MIN"
    headers = _auth_headers(base_url=base_url, api_token=api_token)
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return data
    return data.get("tasks", [])


def _sdk_export(base_url: str, api_token: str, project_id: int) -> list[dict[str, Any]]:
    """
    Use Label Studio SDK with PAT or legacy token.

    SDK versions differ; this supports both common client entry points.
    """
    client: Any
    try:
        from label_studio_sdk import LabelStudio

        client = LabelStudio(base_url=base_url, api_key=api_token)
    except Exception:
        from label_studio_sdk import Client

        client = Client(url=base_url, api_key=api_token)

    project: Any | None = None
    if hasattr(client, "get_project"):
        project = client.get_project(project_id)
    elif hasattr(client, "projects") and hasattr(client.projects, "get"):
        project = client.projects.get(id=project_id)

    if project is None:
        raise RuntimeError("SDK client did not expose a project API.")

    if hasattr(project, "export_tasks"):
        data = project.export_tasks(export_type="JSON_MIN")
    elif hasattr(project, "export"):
        data = project.export(export_type="JSON_MIN")
    else:
        raise RuntimeError("SDK project object does not support export_tasks/export.")

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("tasks", [])
    return []


def export_tasks(base_url: str, api_token: str, project_id: int, *, no_sdk: bool = False) -> list[dict[str, Any]]:
    if not no_sdk:
        try:
            return _sdk_export(base_url=base_url, api_token=api_token, project_id=project_id)
        except Exception as exc:
            print(f"SDK export failed, falling back to HTTP API: {exc}")

    if _looks_like_pat(api_token):
        return _http_export_with_pat(base_url=base_url, pat_token=api_token, project_id=project_id)
    return _http_export_with_legacy(base_url=base_url, api_token=api_token, project_id=project_id)


def resolve_project_id(base_url: str, api_token: str) -> int:
    """
    Resolve an available Label Studio project id.
    Picks the first available project returned by /api/projects.
    """
    url = f"{base_url.rstrip('/')}/api/projects"
    headers = _auth_headers(base_url=base_url, api_token=api_token)
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    payload = response.json() or {}
    projects = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(projects, list) or not projects:
        raise RuntimeError("No Label Studio projects are available for export.")
    first = projects[0]
    project_id = int(first.get("id") or 0)
    if project_id <= 0:
        raise RuntimeError("Unable to resolve a valid Label Studio project id from /api/projects.")
    return project_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--no-sdk",
        action="store_true",
        help="Skip Label Studio SDK and use HTTP API directly.",
    )
    args = parser.parse_args()

    base_url = os.getenv("LABEL_STUDIO_URL", "").strip()
    api_token = (
        os.getenv("LABEL_STUDIO_API_KEY", "").strip()
        or os.getenv("LABEL_STUDIO_API_TOKEN", "").strip()
    )
    project_id = int(os.getenv("LABEL_STUDIO_PROJECT_ID", "0") or "0")

    if not base_url or not api_token or project_id <= 0:
        raise SystemExit(
            "Set LABEL_STUDIO_URL, LABEL_STUDIO_PROJECT_ID, and LABEL_STUDIO_API_KEY "
            "(or LABEL_STUDIO_API_TOKEN)."
        )

    try:
        tasks = export_tasks(
            base_url=base_url,
            api_token=api_token,
            project_id=project_id,
            no_sdk=args.no_sdk,
        )
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status != 404:
            raise
        print(
            f"Configured LABEL_STUDIO_PROJECT_ID={project_id} was not found (404). "
            "Trying automatic project discovery..."
        )
        resolved_id = resolve_project_id(base_url=base_url, api_token=api_token)
        print(
            f"Resolved Label Studio project id to {resolved_id}. "
            f"Update LABEL_STUDIO_PROJECT_ID to this value to avoid future lookups."
        )
        tasks = export_tasks(
            base_url=base_url,
            api_token=api_token,
            project_id=resolved_id,
            no_sdk=True,
        )
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(tasks)} tasks to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

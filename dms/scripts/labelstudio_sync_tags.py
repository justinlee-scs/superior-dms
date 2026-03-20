from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

import requests
from sqlalchemy.orm import Session

# Ensure project root is on PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.db.session import SessionLocal
from app.db.repositories.tags import list_tag_pool
from app.db.repositories.documents import list_existing_tags


def _auth_header(api_token: str) -> dict[str, str]:
    scheme = os.getenv("LABEL_STUDIO_AUTH_SCHEME", "Token").strip() or "Token"
    return {"Authorization": f"{scheme} {api_token}"}


def _fetch_project_config(base_url: str, api_token: str, project_id: int) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/projects/{project_id}"
    response = requests.get(url, headers=_auth_header(api_token), timeout=30)
    response.raise_for_status()
    return response.json()


def _update_project_config(
    base_url: str, api_token: str, project_id: int, label_config: str
) -> None:
    url = f"{base_url.rstrip('/')}/api/projects/{project_id}"
    response = requests.patch(
        url,
        headers=_auth_header(api_token),
        json={"label_config": label_config},
        timeout=30,
    )
    response.raise_for_status()


def _build_choice_block(tags: list[str]) -> str:
    return "\n".join(f'    <Choice value="{tag}"/>' for tag in tags)


def _replace_tag_choices(label_config: str, tags: list[str]) -> str:
    pattern = re.compile(
        r'(<Choices[^>]*name="tags"[^>]*>)(.*?)(</Choices>)',
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(label_config)
    if not match:
        raise ValueError("Could not find <Choices name=\"tags\"> block in label_config.")

    before, _, after = match.groups()
    choices_block = _build_choice_block(tags)
    updated = f"{before}\n{choices_block}\n  {after}"
    return label_config[: match.start()] + updated + label_config[match.end() :]


def _append_tag_choices(label_config: str, tags: list[str]) -> str:
    pattern = re.compile(
        r'(<Choices[^>]*name="tags"[^>]*>)(.*?)(</Choices>)',
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(label_config)
    if not match:
        raise ValueError("Could not find <Choices name=\"tags\"> block in label_config.")

    before, middle, after = match.groups()
    existing = set(re.findall(r'<Choice value="([^"]+)"', middle))
    to_add = [tag for tag in tags if tag not in existing]
    if not to_add:
        return label_config

    choices_block = _build_choice_block(sorted(existing) + to_add)
    updated = f"{before}\n{choices_block}\n  {after}"
    return label_config[: match.start()] + updated + label_config[match.end() :]


def _collect_tags(db: Session) -> list[str]:
    pool = set(list_tag_pool(db=db))
    pool.update(list_existing_tags(db=db))
    tags = sorted(
        tag for tag in pool if tag.startswith("project:") or tag.startswith("company:")
    )
    return tags


def main() -> None:
    base_url = os.getenv("LABEL_STUDIO_URL", "").strip()
    api_token = os.getenv("LABEL_STUDIO_API_TOKEN", "").strip()
    project_id = int(os.getenv("LABEL_STUDIO_PROJECT_ID", "0"))
    if not base_url or not api_token or project_id <= 0:
        raise RuntimeError(
            "Set LABEL_STUDIO_URL, LABEL_STUDIO_API_TOKEN, LABEL_STUDIO_PROJECT_ID before running."
        )

    db: Session = SessionLocal()
    try:
        tags = _collect_tags(db)
    finally:
        db.close()

    if not tags:
        raise RuntimeError("No project/company tags found in tag pool.")

    project = _fetch_project_config(base_url, api_token, project_id)
    label_config = project.get("label_config") or ""
    if not label_config:
        raise RuntimeError("Label Studio project has no label_config.")

    mode = os.getenv("LABEL_STUDIO_TAG_SYNC_MODE", "replace").strip().lower()
    if mode == "append":
        updated_config = _append_tag_choices(label_config, tags)
    else:
        updated_config = _replace_tag_choices(label_config, tags)
    _update_project_config(base_url, api_token, project_id, updated_config)
    print(f"Updated Label Studio project {project_id} with {len(tags)} tag choices.")


if __name__ == "__main__":
    main()

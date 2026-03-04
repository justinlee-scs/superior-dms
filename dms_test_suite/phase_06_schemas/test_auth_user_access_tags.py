import uuid

import pytest
from pydantic import ValidationError

from app.db.models.user_permission_override import PermissionEffect
from app.schemas.access import EffectivePermissionsResponse
from app.schemas.auth import TokenResponse
from app.schemas.tags import DocumentVersionTagsResponse, TagUpdateRequest
from app.schemas.user import PermissionOverrideInput, UserCreate, UserOverrideSet


def test_token_response_default_type() -> None:
    token = TokenResponse(access_token="abc123")
    assert token.token_type == "bearer"


def test_effective_permissions_response_deduplicates_to_set() -> None:
    payload = EffectivePermissionsResponse(permissions={"document.read", "document.read", "document.upload"})
    assert payload.permissions == {"document.read", "document.upload"}


def test_user_create_validates_email() -> None:
    with pytest.raises(ValidationError):
        UserCreate(username="u", email="not-an-email", password="long-enough")


def test_user_override_set_serializes_permission_effect_enum() -> None:
    data = UserOverrideSet(
        overrides=[
            PermissionOverrideInput(permission_key="document.read", effect=PermissionEffect.ALLOW),
            PermissionOverrideInput(permission_key="document.delete", effect=PermissionEffect.DENY),
        ]
    )
    assert data.overrides[0].effect == PermissionEffect.ALLOW
    assert data.overrides[1].effect == PermissionEffect.DENY


def test_tags_schemas_default_to_empty_list() -> None:
    req = TagUpdateRequest()
    resp = DocumentVersionTagsResponse(document_id=uuid.uuid4(), version_id=uuid.uuid4())
    assert req.tags == []
    assert resp.tags == []

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.auth import ProfileUpdateRequest, update_profile


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._result


class _FakeDB:
    def __init__(self, query_result=None):
        self._query_result = query_result
        self.committed = False
        self.refreshed = False

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self._query_result)

    def commit(self):
        self.committed = True

    def refresh(self, _obj):
        self.refreshed = True


def _user():
    return SimpleNamespace(
        id="user-1",
        email="test@example.com",
        username="current_name",
        hashed_password="hash",
        roles=[SimpleNamespace(name="viewer")],
    )


def test_update_profile_rejects_empty_username() -> None:
    db = _FakeDB()
    user = _user()
    payload = ProfileUpdateRequest(username="   ")

    with pytest.raises(HTTPException) as exc:
        update_profile(payload=payload, user=user, db=db)

    assert exc.value.status_code == 400
    assert "Username cannot be empty" in exc.value.detail


def test_update_profile_rejects_username_conflict() -> None:
    db = _FakeDB(query_result=SimpleNamespace(id="other"))
    user = _user()
    payload = ProfileUpdateRequest(username="taken_name")

    with pytest.raises(HTTPException) as exc:
        update_profile(payload=payload, user=user, db=db)

    assert exc.value.status_code == 409
    assert "Username already exists" in exc.value.detail


def test_update_profile_requires_current_password_for_change() -> None:
    db = _FakeDB()
    user = _user()
    payload = ProfileUpdateRequest(new_password="new-password-123")

    with pytest.raises(HTTPException) as exc:
        update_profile(payload=payload, user=user, db=db)

    assert exc.value.status_code == 400
    assert "Current password is required" in exc.value.detail


def test_update_profile_rejects_short_new_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.auth.verify_password", lambda *_args, **_kwargs: True)
    db = _FakeDB()
    user = _user()
    payload = ProfileUpdateRequest(current_password="old", new_password="short")

    with pytest.raises(HTTPException) as exc:
        update_profile(payload=payload, user=user, db=db)

    assert exc.value.status_code == 400
    assert "at least 8 characters" in exc.value.detail


def test_update_profile_applies_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.auth.verify_password", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("app.api.auth.hash_password", lambda _raw: "new-hash")
    monkeypatch.setattr("app.api.auth.resolve_permissions", lambda *_args, **_kwargs: {"b", "a"})

    db = _FakeDB()
    user = _user()
    payload = ProfileUpdateRequest(
        username="updated_name",
        current_password="old-pass",
        new_password="new-password-123",
    )

    result = update_profile(payload=payload, user=user, db=db)

    assert user.username == "updated_name"
    assert user.hashed_password == "new-hash"
    assert db.committed is True
    assert db.refreshed is True
    assert result["permissions"] == ["a", "b"]


def test_update_profile_rejects_incorrect_current_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.auth.verify_password", lambda *_args, **_kwargs: False)
    db = _FakeDB()
    user = _user()
    payload = ProfileUpdateRequest(current_password="wrong", new_password="new-password-123")

    with pytest.raises(HTTPException) as exc:
        update_profile(payload=payload, user=user, db=db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Current password is incorrect"


def test_update_profile_requires_at_least_one_change() -> None:
    db = _FakeDB()
    user = _user()
    payload = ProfileUpdateRequest()

    with pytest.raises(HTTPException) as exc:
        update_profile(payload=payload, user=user, db=db)

    assert exc.value.status_code == 400
    assert exc.value.detail == "No profile changes provided"

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.auth import LoginRequest, login, me


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

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self._query_result)


def test_login_rejects_missing_user() -> None:
    db = _FakeDB(query_result=None)
    req = LoginRequest(email="u@example.com", password="pw")

    with pytest.raises(HTTPException) as exc:
        login(req, db=db)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid credentials"


def test_login_rejects_inactive_user() -> None:
    user = SimpleNamespace(is_active=False, hashed_password="x")
    db = _FakeDB(query_result=user)
    req = LoginRequest(email="u@example.com", password="pw")

    with pytest.raises(HTTPException) as exc:
        login(req, db=db)
    assert exc.value.status_code == 403
    assert exc.value.detail == "User inactive"


def test_login_rejects_invalid_password(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(is_active=True, hashed_password="x")
    db = _FakeDB(query_result=user)
    req = LoginRequest(email="u@example.com", password="pw")
    monkeypatch.setattr("app.api.auth.verify_password", lambda *_args, **_kwargs: False)

    with pytest.raises(HTTPException) as exc:
        login(req, db=db)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid password"


def test_login_success_returns_token(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id="u1", is_active=True, hashed_password="hash")
    db = _FakeDB(query_result=user)
    req = LoginRequest(email="u@example.com", password="pw")
    monkeypatch.setattr("app.api.auth.verify_password", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("app.api.auth.create_access_token", lambda _uid: "jwt-token")

    result = login(req, db=db)
    assert result == {"access_token": "jwt-token", "token_type": "bearer"}


def test_me_returns_identity_roles_and_permissions(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(
        id="u1",
        email="u@example.com",
        username="user",
        roles=[SimpleNamespace(name="editor"), SimpleNamespace(name="viewer")],
    )
    monkeypatch.setattr("app.api.auth.resolve_permissions", lambda *_args, **_kwargs: {"b", "a"})

    result = me(user=user, db=object())

    assert result["email"] == "u@example.com"
    assert result["roles"] == ["editor", "viewer"]
    assert result["permissions"] == ["a", "b"]

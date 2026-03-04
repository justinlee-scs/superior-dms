import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.auth.deps import get_current_user


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


def test_get_current_user_rejects_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_args, **_kwargs):
        from jose import JWTError

        raise JWTError("bad token")

    monkeypatch.setattr("app.auth.deps.jwt.decode", _raise)

    with pytest.raises(HTTPException) as exc:
        get_current_user(token="bad-token", db=_FakeDB())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token"


def test_get_current_user_rejects_missing_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.auth.deps.jwt.decode", lambda *_args, **_kwargs: {"exp": 9999999999})

    with pytest.raises(HTTPException) as exc:
        get_current_user(token="no-sub-token", db=_FakeDB())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Missing subject in token"


def test_get_current_user_rejects_inactive_or_missing_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.auth.deps.jwt.decode", lambda *_args, **_kwargs: {"sub": str(uuid.uuid4())})

    with pytest.raises(HTTPException) as exc:
        get_current_user(token="valid-shape-token", db=_FakeDB(query_result=None))

    assert exc.value.status_code == 401
    assert exc.value.detail == "User not found or inactive"


def test_get_current_user_returns_active_user(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=uuid.uuid4(), is_active=True, email="user@example.com")
    monkeypatch.setattr("app.auth.deps.jwt.decode", lambda *_args, **_kwargs: {"sub": str(user.id)})

    current = get_current_user(token="valid-token", db=_FakeDB(query_result=user))

    assert current is user

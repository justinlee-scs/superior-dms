from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.security.auth import get_current_user


class _FakeQuery:
    def __init__(self, first_result):
        self._first_result = first_result

    def first(self):
        return self._first_result


class _FakeDB:
    def __init__(self, first_result):
        self._first_result = first_result

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self._first_result)


def test_get_current_user_returns_first_user() -> None:
    user = SimpleNamespace(id="u-1", email="user@example.com")
    db = _FakeDB(first_result=user)

    result = get_current_user(db=db)

    assert result is user


def test_get_current_user_raises_when_no_users() -> None:
    db = _FakeDB(first_result=None)

    with pytest.raises(HTTPException) as exc:
        get_current_user(db=db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "No users exist"

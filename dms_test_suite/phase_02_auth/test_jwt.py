import uuid

import pytest
from jose import JWTError

from app.auth.jwt import create_access_token, decode_access_token, hash_password, verify_password


def test_hash_and_verify_password_roundtrip() -> None:
    plain = "S3cure-Pass-123"
    hashed = hash_password(plain)

    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_create_and_decode_access_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id)

    decoded = decode_access_token(token)
    assert decoded == user_id


def test_decode_access_token_rejects_missing_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.auth.jwt.jwt.decode", lambda *_args, **_kwargs: {"exp": 9999999999})

    with pytest.raises(JWTError) as exc:
        decode_access_token("token-without-sub")

    assert "Missing subject" in str(exc.value)

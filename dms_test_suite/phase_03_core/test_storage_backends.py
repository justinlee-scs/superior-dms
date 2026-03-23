import pytest

from app.storage import backends


def test_build_object_storage_from_env_minio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OBJECT_STORAGE_BACKEND", "minio")
    monkeypatch.setenv("MINIO_ENDPOINT", "127.0.0.1:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "ak")
    monkeypatch.setenv("MINIO_SECRET_KEY", "sk")
    monkeypatch.setenv("MINIO_SECURE", "true")

    created = {}

    class _Minio:
        def __init__(self, *, endpoint, access_key, secret_key, secure):
            created["endpoint"] = endpoint
            created["access_key"] = access_key
            created["secret_key"] = secret_key
            created["secure"] = secure

    monkeypatch.setattr(backends, "MinioObjectStorage", _Minio)
    storage = backends.build_object_storage_from_env()
    assert isinstance(storage, _Minio)
    assert created["secure"] is True


def test_build_object_storage_from_env_s3(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OBJECT_STORAGE_BACKEND", "s3")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "ak")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "sk")
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://localhost")

    created = {}

    class _S3:
        def __init__(self, *, region_name, endpoint_url, access_key_id, secret_access_key, session_token):
            created["region_name"] = region_name
            created["endpoint_url"] = endpoint_url
            created["access_key_id"] = access_key_id
            created["secret_access_key"] = secret_access_key
            created["session_token"] = session_token

    monkeypatch.setattr(backends, "S3ObjectStorage", _S3)
    storage = backends.build_object_storage_from_env()
    assert isinstance(storage, _S3)
    assert created["region_name"] == "us-west-2"


def test_build_object_storage_from_env_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OBJECT_STORAGE_BACKEND", "unknown")
    with pytest.raises(ValueError):
        backends.build_object_storage_from_env()

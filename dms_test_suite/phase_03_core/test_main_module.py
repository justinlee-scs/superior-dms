from types import SimpleNamespace

from app.main import health, list_docs, root


def test_main_root_health_and_list_docs() -> None:
    assert root() == {"message": "DMS API running"}
    assert health() == {"status": "ok"}
    assert list_docs(user=SimpleNamespace(email="a@b.com")) == {"msg": "Hello a@b.com"}

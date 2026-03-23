from types import SimpleNamespace

import pytest

from app.export_unusableversion import mayan


def test_lookup_mayan_metadata_type_id_unimplemented() -> None:
    with pytest.raises(NotImplementedError):
        mayan.lookup_mayan_metadata_type_id("label")


def test_export_document_to_mayan(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def execute(self, query, params):
            self.last_query = query
            self.last_params = params

        def fetchone(self):
            return ["invoice"]

        def fetchall(self):
            return [("field_a", "value_a"), ("field_b", "value_b")]

    class _Conn:
        def cursor(self):
            return _Cursor()

    monkeypatch.setattr(mayan, "get_conn", lambda: _Conn())
    monkeypatch.setattr(mayan, "FIELD_MAPPING", {"invoice": {"field_a": "Label A"}})
    monkeypatch.setattr(mayan, "lookup_mayan_metadata_type_id", lambda label: 123 if label == "Label A" else 0)

    class _Client:
        def set_metadata(self, mayan_doc_id, metadata_type_id, value):
            calls.append((mayan_doc_id, metadata_type_id, value))

    mayan.export_document_to_mayan("doc", 9, _Client())
    assert calls == [(9, 123, "value_a")]

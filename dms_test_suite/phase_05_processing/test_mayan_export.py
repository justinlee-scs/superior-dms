from types import SimpleNamespace

import pytest

import importlib
import sys
import types


def _load_mayan():
    dummy_db = types.ModuleType("app.db")
    dummy_db.get_conn = lambda: None
    sys.modules["app.db"] = dummy_db
    dummy_export = types.ModuleType("app.export")
    dummy_field_mapping = types.ModuleType("app.export.field_mapping")
    dummy_field_mapping.FIELD_MAPPING = {}
    sys.modules["app.export"] = dummy_export
    sys.modules["app.export.field_mapping"] = dummy_field_mapping
    return importlib.import_module("app.export_unusableversion.mayan")


def test_lookup_mayan_metadata_type_id_unimplemented() -> None:
    mayan = _load_mayan()
    with pytest.raises(NotImplementedError):
        mayan.lookup_mayan_metadata_type_id("label")


def test_export_document_to_mayan(monkeypatch: pytest.MonkeyPatch) -> None:
    mayan = _load_mayan()
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

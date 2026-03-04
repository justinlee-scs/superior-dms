import importlib
import runpy
import sys
import types


def test_init_db_invokes_metadata_create_all(monkeypatch):
    # app.db.init_db imports legacy module paths; stub them for import safety in test.
    monkeypatch.setitem(sys.modules, "app.db.models.document", types.ModuleType("app.db.models.document"))
    monkeypatch.setitem(
        sys.modules,
        "app.db.models.document_version",
        types.ModuleType("app.db.models.document_version"),
    )
    sys.modules["app.db.models.document"].Document = object
    sys.modules["app.db.models.document_version"].DocumentVersion = object

    module = importlib.import_module("app.db.init_db")
    importlib.reload(module)

    called = {"count": 0}

    class _Metadata:
        def create_all(self, bind):
            assert bind is not None
            called["count"] += 1

    monkeypatch.setattr(module, "Base", types.SimpleNamespace(metadata=_Metadata()))
    monkeypatch.setattr(module, "engine", object())

    module.init_db()

    assert called["count"] == 1


def test_init_db_main_entrypoint_calls_init_db(monkeypatch):
    monkeypatch.setitem(sys.modules, "app.db.models.document", types.ModuleType("app.db.models.document"))
    monkeypatch.setitem(
        sys.modules,
        "app.db.models.document_version",
        types.ModuleType("app.db.models.document_version"),
    )
    sys.modules["app.db.models.document"].Document = object
    sys.modules["app.db.models.document_version"].DocumentVersion = object

    called = {"count": 0}

    class _Metadata:
        def create_all(self, bind):
            assert bind is not None
            called["count"] += 1

    import app.db.session as db_session

    monkeypatch.setattr(db_session, "Base", types.SimpleNamespace(metadata=_Metadata()))
    monkeypatch.setattr(db_session, "engine", object())
    runpy.run_module("app.db.init_db", run_name="__main__")

    assert called["count"] == 1

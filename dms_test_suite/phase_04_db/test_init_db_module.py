import importlib
import runpy


def test_init_db_invokes_alembic_upgrade(monkeypatch):
    module = importlib.import_module("app.db.init_db")
    importlib.reload(module)

    called = {"args": None}
    monkeypatch.setattr(module, "Config", lambda path: path)
    monkeypatch.setattr(
        module,
        "command",
        type("C", (), {"upgrade": lambda _self, cfg, rev: called.update(args=(rev, cfg))})(),
    )

    module.init_db()

    assert called["args"] == ("head", "alembic.ini")


def test_init_db_main_entrypoint_calls_init_db(monkeypatch):
    called = {"args": None}

    monkeypatch.setattr("alembic.config.Config", lambda path: path)
    monkeypatch.setattr(
        "alembic.command.upgrade",
        lambda cfg, rev: called.update(args=(rev, cfg)),
    )
    runpy.run_module("app.db.init_db", run_name="__main__")

    assert called["args"] == ("head", "alembic.ini")

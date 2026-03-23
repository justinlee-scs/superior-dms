import importlib.util
from types import SimpleNamespace

import pytest


def _load_env_module(is_offline: bool, monkeypatch: pytest.MonkeyPatch):
    calls = {"configure": 0, "run_migrations": 0}

    class _Context:
        def __init__(self):
            self.config = SimpleNamespace(
                config_file_name=None,
                config_ini_section="alembic",
                set_main_option=lambda *_a, **_k: None,
                get_main_option=lambda *_a, **_k: "sqlite://",
                get_section=lambda *_a, **_k: {},
            )

        def configure(self, **_kwargs):
            calls["configure"] += 1

        def begin_transaction(self):
            class _Tx:
                def __enter__(self_inner):
                    return self_inner

                def __exit__(self_inner, *_exc):
                    return False

            return _Tx()

        def run_migrations(self):
            calls["run_migrations"] += 1

        def is_offline_mode(self):
            return is_offline

    class _Engine:
        def connect(self):
            class _Conn:
                def __enter__(self_inner):
                    return self_inner

                def __exit__(self_inner, *_exc):
                    return False

            return _Conn()

    dummy_alembic = SimpleNamespace(context=_Context())
    monkeypatch.setitem(__import__("sys").modules, "alembic", dummy_alembic)
    monkeypatch.setitem(__import__("sys").modules, "alembic.context", dummy_alembic.context)

    dummy_sqlalchemy = SimpleNamespace(engine_from_config=lambda *_a, **_k: _Engine(), pool=SimpleNamespace(NullPool=object))
    monkeypatch.setitem(__import__("sys").modules, "sqlalchemy", dummy_sqlalchemy)
    monkeypatch.setitem(__import__("sys").modules, "sqlalchemy.pool", dummy_sqlalchemy.pool)
    monkeypatch.setitem(__import__("sys").modules, "sqlalchemy.engine", dummy_sqlalchemy)

    path = "/home/justinlee/.LINUXPRACTICE/dms/app/db/migrations/env.py"
    spec = importlib.util.spec_from_file_location(f"env_{is_offline}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return calls, module


def test_run_migrations_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, module = _load_env_module(is_offline=True, monkeypatch=monkeypatch)
    module.run_migrations_offline()
    assert calls["configure"] >= 1
    assert calls["run_migrations"] >= 1


def test_run_migrations_online(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, module = _load_env_module(is_offline=False, monkeypatch=monkeypatch)
    module.run_migrations_online()
    assert calls["configure"] >= 1
    assert calls["run_migrations"] >= 1

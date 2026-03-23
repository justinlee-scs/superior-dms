import importlib.util
import types
from pathlib import Path


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


VERSIONS_DIR = Path("/home/justinlee/.LINUXPRACTICE/dms/app/db/migrations/versions")
baseline = _load_module(str(VERSIONS_DIR / "20260306_0001_baseline.py"), "baseline")
invoice_types = _load_module(str(VERSIONS_DIR / "20260317_0002_add_invoice_types.py"), "invoice_types")
role_user = _load_module(str(VERSIONS_DIR / "20260323_0003_add_role_user_management.py"), "role_user")
user_mgmt = _load_module(str(VERSIONS_DIR / "20260323_0004_add_user_management_tables.py"), "user_mgmt")


def test_baseline_upgrade_and_downgrade(monkeypatch) -> None:
    calls = {"create": False, "drop": False}

    class _Meta:
        def create_all(self, bind):
            calls["create"] = True

        def drop_all(self, bind):
            calls["drop"] = True

    monkeypatch.setattr(baseline, "Base", types.SimpleNamespace(metadata=_Meta()))
    monkeypatch.setattr(baseline.op, "get_bind", lambda: object())

    baseline.upgrade()
    baseline.downgrade()

    assert calls["create"] is True
    assert calls["drop"] is True


def test_invoice_types_migration_executes_sql(monkeypatch) -> None:
    executed = []
    monkeypatch.setattr(invoice_types.op, "execute", lambda sql: executed.append(sql))
    invoice_types.upgrade()
    assert any("incoming_invoice" in stmt for stmt in executed)


def test_role_user_management_migration(monkeypatch) -> None:
    calls = {"create": False, "drop": False}
    monkeypatch.setattr(role_user.op, "create_table", lambda *_a, **_k: calls.__setitem__("create", True))
    monkeypatch.setattr(role_user.op, "drop_table", lambda *_a, **_k: calls.__setitem__("drop", True))
    role_user.upgrade()
    role_user.downgrade()
    assert calls["create"] is True
    assert calls["drop"] is True


def test_user_management_tables_migration(monkeypatch) -> None:
    created = []
    dropped = []
    monkeypatch.setattr(user_mgmt.op, "create_table", lambda name, *_a, **_k: created.append(name))
    monkeypatch.setattr(user_mgmt.op, "drop_table", lambda name, *_a, **_k: dropped.append(name))
    user_mgmt.upgrade()
    user_mgmt.downgrade()
    assert "user_role_management" in created
    assert "user_user_management" in created
    assert "user_user_management" in dropped
    assert "user_role_management" in dropped

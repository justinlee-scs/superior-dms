import importlib


def test_core_package_is_importable() -> None:
    module = importlib.import_module("app.core")
    assert module is not None


def test_core_phase_has_no_runtime_modules_yet() -> None:
    # app/core currently contains only an empty __init__.py.
    module = importlib.import_module("app.core")
    assert getattr(module, "__file__", "").endswith("app/core/__init__.py")

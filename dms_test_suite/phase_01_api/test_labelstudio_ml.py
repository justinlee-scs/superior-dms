from types import SimpleNamespace

import pytest

from app.api import labelstudio_ml as ls


def test_env_and_choice_result_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LS_TEST_KEY", "  value  ")
    assert ls._env("LS_TEST_KEY", "fallback") == "value"
    assert ls._env("MISSING", "fallback") == "fallback"

    result = ls._choice_result(from_name="a", to_name="b", choices=["x"])
    assert result["from_name"] == "a"
    assert result["to_name"] == "b"
    assert result["type"] == "choices"
    assert result["value"]["choices"] == ["x"]


def test_build_existing_tag_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ls, "list_tag_pool", lambda db: ["project:alpha", "company:acme"])
    monkeypatch.setattr(ls, "list_existing_tags", lambda db: ["company:acme", "tag:extra"])

    pool = ls._build_existing_tag_pool(db=SimpleNamespace())
    assert pool == ["company:acme", "project:alpha", "tag:extra"]


def test_extract_text_and_parse_tasks() -> None:
    assert ls._extract_text({"ocr_text": "ok"}) == "ok"
    assert ls._extract_text({"text": "hi"}) == "hi"
    assert ls._extract_text({"content": "hey"}) == "hey"
    assert ls._extract_text({"document_text": "doc"}) == "doc"
    assert ls._extract_text({}) == ""

    tasks, wrapped = ls._parse_tasks([{"data": {"text": "a"}}])
    assert tasks and wrapped is False

    tasks, wrapped = ls._parse_tasks({"tasks": [{"data": {"text": "a"}}]})
    assert len(tasks) == 1 and wrapped is True

    tasks, wrapped = ls._parse_tasks({"data": {"text": "a"}})
    assert len(tasks) == 1 and wrapped is False

    tasks, wrapped = ls._parse_tasks("invalid")
    assert tasks == [] and wrapped is False


def test_predict_for_task(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LS_FROM_DOCUMENT_TYPE", "doc_type")
    monkeypatch.setenv("LS_FROM_TAGS", "tags")
    monkeypatch.setenv("LS_FROM_HANDWRITING", "handwriting")
    monkeypatch.setenv("LS_TO_NAME", "to")
    monkeypatch.setenv("LS_MODEL_VERSION", "v1")

    monkeypatch.setattr(ls, "classify_document", lambda _t: SimpleNamespace(value="invoice"))
    monkeypatch.setattr(ls, "derive_tags", lambda *_a, **_k: ["project:alpha", "company:acme"])

    result = ls._predict_for_task(
        {"text": "invoice", "filename": "file.pdf", "image": "present"},
        existing_tags=["company:acme"],
    )

    assert result["model_version"] == "v1"
    choices = [r["value"]["choices"][0] for r in result["result"]]
    assert "invoice" in choices
    assert "project:alpha" in choices
    assert "unknown" in choices


def test_setup_and_train() -> None:
    assert ls.setup({"a": 1, "b": 2})["payload_keys"] == ["a", "b"]
    assert ls.train({"x": 1})["status"] == "ok"

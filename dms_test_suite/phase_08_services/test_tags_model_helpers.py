import pytest

from app.services.extraction import tags


def test_derive_company_tag_from_text_and_existing_tags() -> None:
    tag = tags._derive_company_tag("Company: Acme Corp", None, [])
    assert tag == "company:acme"

    tag = tags._derive_company_tag("invoice from vendor mega", None, ["company:mega_corp"])
    assert tag == "company:mega_corp"


def test_load_tagger_model_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAGGER_MODEL_PATH", raising=False)
    tags._load_tagger_model.cache_clear()
    assert tags._load_tagger_model() is None


def test_predict_model_tags_proba(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Vectorizer:
        def transform(self, _):
            return "features"

    class _Model:
        def predict_proba(self, _features):
            return [[0.6, 0.4]]

    monkeypatch.setenv("TAGGER_THRESHOLD", "0.5")
    monkeypatch.setattr(tags, "_load_tagger_model", lambda: {"vectorizer": _Vectorizer(), "model": _Model(), "labels": ["a", "b"]})

    result = tags._predict_model_tags("text")
    assert result == {"a"}

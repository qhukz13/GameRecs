import pytest

from app.application.services.llm_provider import _discover_ollama_model


class _MockResponse:
    def __init__(self, data, raise_exc=False):
        self._data = data
        self._raise = raise_exc

    def raise_for_status(self):
        if self._raise:
            raise RuntimeError("http error")

    def json(self):
        return self._data


def test_discover_prefers_priority(monkeypatch):
    # models list as returned by Ollama
    data = [
        {"name": "small-model"},
        {"name": "mistral-7b"},
        {"name": "other"},
    ]

    def fake_get(url, timeout=0):
        assert url.endswith("/api/models")
        return _MockResponse(data)

    monkeypatch.setattr("requests.get", fake_get)

    picked = _discover_ollama_model("http://localhost:11434")
    assert picked is not None
    assert "mistral" in picked.lower()


def test_discover_handles_models_key(monkeypatch):
    data = {"models": [{"name": "some-embed"}, {"name": "llama2"}]}

    def fake_get(url, timeout=0):
        return _MockResponse(data)

    monkeypatch.setattr("requests.get", fake_get)

    picked = _discover_ollama_model("http://localhost:11434")
    assert picked is not None
    # should prefer 'embed' containing name
    assert "embed" in picked.lower()


def test_discover_fallback_to_first(monkeypatch):
    data = ["alpha", "beta"]

    def fake_get(url, timeout=0):
        return _MockResponse(data)

    monkeypatch.setattr("requests.get", fake_get)

    picked = _discover_ollama_model("http://localhost:11434")
    assert picked == "alpha"


def test_discover_returns_none_on_error(monkeypatch):
    def fake_get(url, timeout=0):
        raise RuntimeError("no connection")

    monkeypatch.setattr("requests.get", fake_get)

    picked = _discover_ollama_model("http://localhost:11434")
    assert picked is None

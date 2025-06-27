import types
import sys
import steps.deepresearch_functions as drf

class DummyResp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def test_retrieve_from_archive(monkeypatch):
    def dummy_get(url, params=None, timeout=10):
        assert "archive.org/advancedsearch.php" in url
        assert params["q"] == "hello"
        return DummyResp({"response": {"docs": [
            {"title": "T1", "description": "D1"},
            {"title": "T2", "description": ""}
        ]}})

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(get=dummy_get))
    result = drf.retrieve_from_archive({"extended_query": "hello", "top_k": 2})
    assert result["chunks"] == ["T1 D1", "T2"]


def test_retrieve_from_archive_fallback(monkeypatch):
    def bad_get(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(get=bad_get))
    result = drf.retrieve_from_archive({"extended_query": "oops"})
    assert result["chunks"] == ["chunk for oops"]

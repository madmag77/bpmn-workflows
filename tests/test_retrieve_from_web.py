import types
import sys
import steps.deepresearch_functions as drf


class DummyHTML:
    def __init__(self, text="", links=None):
        self.text = text
        self._links = links or []

    def find(self, selector):
        return [types.SimpleNamespace(attrs={"href": f"/url?q={url}"}) for url in self._links]

    def render(self, **kwargs):
        pass


class DummyResponse:
    def __init__(self, html):
        self.html = html


class DummySession:
    def __init__(self, links, text):
        self.links = links
        self.text = text
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        if "google.com/search" in url:
            return DummyResponse(DummyHTML(links=self.links))
        return DummyResponse(DummyHTML(text=self.text))


def test_retrieve_from_web(monkeypatch):
    dummy = DummySession(["http://example.com/a", "http://example.com/b"], "page")
    fake_mod = types.SimpleNamespace(HTMLSession=lambda: dummy)
    monkeypatch.setitem(sys.modules, "requests_html", fake_mod)

    result = drf.retrieve_from_web({"extended_query": "hello", "top_k": 2})
    assert result["chunks"] == ["page", "page"]
    assert dummy.calls[0].startswith("https://www.google.com/search")

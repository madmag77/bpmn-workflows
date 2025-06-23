import steps.deepresearch_functions as drf


def test_query_extender_fallback(monkeypatch):
    class Dummy:
        def chat(self, msgs):
            raise RuntimeError("fail")

    monkeypatch.setattr(drf, "_structured_llm_extender", lambda: Dummy())
    res = drf.query_extender({
        "query": "base",
        "clarifications": "details",
        "next_query": "direction",
    })
    assert "direction" in res["extended_query"]
    assert "details" in res["extended_query"]


def test_query_extender_llm(monkeypatch):
    class Dummy:
        def chat(self, msgs):
            class R:
                raw = drf.QueryExtension(extended_query="from llm")
            return R()

    monkeypatch.setattr(drf, "_structured_llm_extender", lambda: Dummy())
    res = drf.query_extender({"query": "base", "clarifications": "", "next_query": ""})
    assert res["extended_query"] == "from llm"


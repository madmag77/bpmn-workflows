import steps.deepresearch_functions as drf


def test_process_info_fallback(monkeypatch):
    class Dummy:
        def chat(self, msgs):
            raise RuntimeError("fail")

    monkeypatch.setattr(drf, "_structured_llm_draft", lambda: Dummy())
    res = drf.process_info({
        "query": "q",
        "extended_query": "ex",
        "chunks": ["c1"],
        "answer_draft": "prev",
    })
    assert res["answer_draft"].startswith("prev")
    assert "c1" in res["answer_draft"]


def test_process_info_llm(monkeypatch):
    class Dummy:
        def chat(self, msgs):
            class R:
                raw = drf.AnswerDraft(answer_draft="from llm")

            return R()

    monkeypatch.setattr(drf, "_structured_llm_draft", lambda: Dummy())
    res = drf.process_info({
        "query": "q",
        "extended_query": "ex",
        "chunks": ["c1"],
        "answer_draft": "prev",
    })
    assert res["answer_draft"] == "from llm"

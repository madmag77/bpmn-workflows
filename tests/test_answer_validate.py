import steps.deepresearch_functions as drf


def test_answer_validate_fallback(monkeypatch):
    class Dummy:
        def chat(self, msgs):
            raise RuntimeError("fail")

    monkeypatch.setattr(drf, "_structured_llm_validate", lambda: Dummy())
    res = drf.answer_validate({"query": "q", "answer_draft": "draft"})
    assert res["is_enough"] == "BAD"
    assert res["next_query"]


def test_answer_validate_llm(monkeypatch):
    class Dummy:
        def chat(self, msgs):
            class R:
                raw = drf.AnswerValidation(is_enough="GOOD", next_query="")

            return R()

    monkeypatch.setattr(drf, "_structured_llm_validate", lambda: Dummy())
    res = drf.answer_validate({"query": "q", "answer_draft": "draft"})
    assert res["is_enough"] == "GOOD"
    assert res["next_query"] == ""

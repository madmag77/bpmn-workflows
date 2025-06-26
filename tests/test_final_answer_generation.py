import steps.deepresearch_functions as drf


def test_final_answer_generation_fallback(monkeypatch):
    class Dummy:
        def chat(self, msgs):
            raise RuntimeError("fail")

    monkeypatch.setattr(drf, "_structured_llm_final", lambda: Dummy())
    res = drf.final_answer_generation({"query": "q", "answer_draft": "draft"})
    assert res["final_answer"] == "draft"


def test_final_answer_generation_llm(monkeypatch):
    class Dummy:
        def chat(self, msgs):
            class R:
                raw = drf.FinalAnswer(final_answer="from llm")

            return R()

    monkeypatch.setattr(drf, "_structured_llm_final", lambda: Dummy())
    res = drf.final_answer_generation({"query": "q", "answer_draft": "draft"})
    assert res["final_answer"] == "from llm"

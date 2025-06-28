from run_bpmn_workflow import run_workflow
import steps.deepresearch_functions as drf

XML_PATH = "workflows/deepresearch/deepresearch.xml"

FN_MAP = {name: getattr(drf, name) for name in dir(drf) if not name.startswith("_")}

# Full flow test with mocked LLMs and web retrieval
def test_deepresearch_full_mocked(monkeypatch):
    class DummyAnalyse:
        def chat(self, msgs):
            class R:
                raw = drf.QueryAnalysis(extended_query="ext", questions=[])
            return R()

    class DummyExtender:
        def chat(self, msgs):
            class R:
                raw = drf.QueryExtension(extended_query="ext q")
            return R()

    class DummyDraft:
        def chat(self, msgs):
            class R:
                raw = drf.AnswerDraft(answer_draft="draft")
            return R()

    class DummyValidate:
        def chat(self, msgs):
            class R:
                raw = drf.AnswerValidation(is_enough="GOOD", next_query="")
            return R()

    class DummyFinal:
        def chat(self, msgs):
            class R:
                raw = drf.FinalAnswer(final_answer="polished")
            return R()

    monkeypatch.setattr(drf, "_structured_llm", lambda: DummyAnalyse())
    monkeypatch.setattr(drf, "_structured_llm_extender", lambda: DummyExtender())
    monkeypatch.setattr(drf, "_structured_llm_draft", lambda: DummyDraft())
    monkeypatch.setattr(drf, "_structured_llm_validate", lambda: DummyValidate())
    monkeypatch.setattr(drf, "_structured_llm_final", lambda: DummyFinal())

    FN_MAP["retrieve_from_web"] = lambda state: {"chunks": ["chunk"]}

    result = run_workflow(XML_PATH, fn_map=FN_MAP, params={"query": "hello"})
    assert result.get("final_answer") == "polished"

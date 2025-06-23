import steps.deepresearch_functions as drf
from langgraph.checkpoint.memory import MemorySaver
from .helper import run_workflow

XML_PATH = "workflows/deepresearch/deepresearch.xml"

FN_MAP = {name: getattr(drf, name) for name in dir(drf) if not name.startswith("_")}


def test_analyse_branching():
    calls = {"ask": 0, "extend": 0}

    def analyse_no_questions(state):
        return {"extended_query": state.get("query", ""), "questions": []}

    def analyse_with_questions(state):
        return {"extended_query": state.get("query", ""), "questions": ["clarify?"]}

    def ask_questions(state):
        calls["ask"] += 1
        return drf.ask_questions(state)

    def query_extender(state):
        calls["extend"] += 1
        return drf.query_extender(state)

    # Branch when no questions
    overrides = dict(FN_MAP)
    overrides.update(
        analyse_user_query=analyse_no_questions,
        ask_questions=ask_questions,
        query_extender=query_extender,
    )
    result = run_workflow(XML_PATH, fn_overrides=overrides, params={"query": "hello"})
    assert result.get("final_answer")
    assert calls["ask"] == 0
    assert calls["extend"] > 0

    # Branch with questions
    calls["ask"] = 0
    calls["extend"] = 0
    overrides["analyse_user_query"] = analyse_with_questions
    saver = MemorySaver()
    first = run_workflow(
        XML_PATH,
        fn_overrides=overrides,
        params={"query": "hello"},
        checkpointer=saver,
        thread_id="branch",
    )
    assert "__interrupt__" in first
    assert calls["ask"] == 1
    assert calls["extend"] == 0

    resumed = run_workflow(
        XML_PATH,
        fn_overrides=overrides,
        checkpointer=saver,
        thread_id="branch",
        resume="answer",
    )
    assert resumed.get("final_answer")
    assert calls["extend"] > 0

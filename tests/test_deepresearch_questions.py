import steps.deepresearch_functions as drf
from langgraph.checkpoint.memory import MemorySaver
from .helper import run_workflow

XML_PATH = "workflows/deepresearch/deepresearch.xml"

FN_MAP = {name: getattr(drf, name) for name in dir(drf) if not name.startswith("_")}

def test_clarification_interrupt_resume():
    def analyse(state):
        return {"extended_query": state.get("query", ""), "questions": ["clarify?"]}

    overrides = dict(FN_MAP)
    overrides["analyse_user_query"] = analyse

    saver = MemorySaver()
    first = run_workflow(
        XML_PATH,
        fn_overrides=overrides,
        params={"query": "hello"},
        checkpointer=saver,
        thread_id="clarify",
    )
    assert "__interrupt__" in first

    resumed = run_workflow(
        XML_PATH,
        fn_overrides=overrides,
        checkpointer=saver,
        thread_id="clarify",
        resume="answer",
    )
    assert resumed.get("clarifications") == "answer"
    assert resumed.get("final_answer")

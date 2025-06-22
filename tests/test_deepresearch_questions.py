import steps.deepresearch_functions as drf
from run_bpmn_workflow import build_graph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

XML_PATH = "workflows/deepresearch/deepresearch.xml"

FN_MAP = {name: getattr(drf, name) for name in dir(drf) if not name.startswith("_")}

def test_clarification_interrupt_resume():
    def analyse(state):
        return {"extended_query": state.get("query", ""), "questions": ["clarify?"]}

    overrides = dict(FN_MAP)
    overrides["analyse_user_query"] = analyse

    saver = MemorySaver()
    graph = build_graph(XML_PATH, functions=overrides, checkpointer=saver)

    config = {"configurable": {"thread_id": "clarify"}}

    first = graph.invoke({"query": "hello"}, config)
    assert "__interrupt__" in first

    resumed = graph.invoke(Command(resume="answer"), config)
    assert resumed.get("clarifications") == "answer"
    assert resumed.get("final_answer")

from langgraph.checkpoint.memory import MemorySaver
import json
from run_bpmn_workflow import run_workflow
from langgraph.types import interrupt

XML_PATH = "workflows/deepresearch/deepresearch.xml"

def analyse_no_questions(state):
        return {"extended_query": state.get("query", ""), "questions": []}

def analyse_with_questions(state):
    return {"extended_query": state.get("query", ""), "questions": ["clarify?"]}

def ask_questions(state):
    answer = interrupt({"questions": ["clarify?"]})
    return {"clarifications": answer}

def query_extender(state):
    return {"extended_query": "extended query"}

def retrieve_from_web(state):
    return {"chunks": ["chunk for hello"]}

def process_info(state):
    return {"answer_draft": "answer draft"}

def answer_validate_good(state):
    return {"is_enough": "GOOD", "next_query": ""}

def final_answer_generation(state):
    return {"final_answer": "final answer"}

fn_map = {
    "analyse_user_query": analyse_with_questions,
    "ask_questions": ask_questions,
    "query_extender": query_extender,
    "retrieve_from_web": retrieve_from_web,
    "process_info": process_info,
    "answer_validate": answer_validate_good,
    "final_answer_generation": final_answer_generation,
}

def test_clarification_interrupt_resume():
    def analyse(state):
        return {"extended_query": state.get("query", ""), "questions": ["clarify?"]}

    overrides = dict(fn_map)
    overrides["analyse_user_query"] = analyse

    saver = MemorySaver()
    first = run_workflow(
        XML_PATH,
        fn_map=overrides,
        params={"query": "hello"},
        checkpointer=saver,
        thread_id="clarify",
    )
    assert "__interrupt__" in first
    answer  = {"answer": "answer"}
    resumed = run_workflow(
        XML_PATH,
        fn_map=overrides,
        checkpointer=saver,
        thread_id="clarify",
        resume=json.dumps(answer),
    )
    assert resumed.get("clarifications") == answer
    assert resumed.get("final_answer")

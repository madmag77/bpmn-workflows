from bpmn_workflows.run_bpmn_workflow import run_workflow

XML_PATH = "workflows/deepresearch/deepresearch.xml"

calls = dict()

def analyse_no_questions(state):
        return {"extended_query": state.get("query", ""), "questions": []}

def analyse_with_questions(state):
    return {"extended_query": state.get("query", ""), "questions": ["clarify?"]}

def ask_questions(state):
    return {"clarifications": "Interrested mostly in diagnostics"}

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
    "analyse_user_query": analyse_no_questions,
    "ask_questions": ask_questions,
    "query_extender": query_extender,
    "retrieve_from_web": retrieve_from_web,
    "process_info": process_info,
    "answer_validate": answer_validate_good,
    "final_answer_generation": final_answer_generation,
}

def test_deepresearch_ok():
    overrides = dict(fn_map)
    result = run_workflow(XML_PATH, fn_map=overrides, params={"query": "hello"})
    assert result.get("final_answer")


def test_deepresearch_loop():
    def validate(state):
        if state.get("iteration", 0) < 2:
            return {"is_enough": "BAD", "next_query": "next"}
        return {"is_enough": "GOOD", "next_query": ""}

    overrides = dict(fn_map)
    overrides["answer_validate"] = validate
    result = run_workflow(XML_PATH, fn_map=overrides, params={"query": "hello"})
    assert result.get("final_answer")
    assert result.get("iteration", 0) == 2


from awsl.run_awsl_workflow import run_workflow

AWSL_PATH = "awsl/deepresearch.awsl"


def analyse_no_questions(state):
    return {"extended_query": state.get("query", ""), "questions": []}


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


FN_MAP = {
    "analyse_user_query": analyse_no_questions,
    "ask_questions": ask_questions,
    "query_extender": query_extender,
    "retrieve_from_web": retrieve_from_web,
    "process_info": process_info,
    "answer_validate": answer_validate_good,
    "final_answer_generation": final_answer_generation,
}


def test_awsl_runner_ok():
    overrides = dict(FN_MAP)
    result = run_workflow(AWSL_PATH, fn_map=overrides, params={"query": "hello"})
    assert result.get("final_answer")



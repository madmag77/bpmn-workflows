from awsl.run_awsl_workflow import run_workflow

AWSL_PATH = "awsl/sample_with_cycle.awsl"


def query_extender(state: dict, config: dict) -> dict:
    return {"extended_query": "extended query"}


def retrieve_from_web(state: dict, config: dict) -> dict:
    return {"chunks": ["chunk for hello"], "need_filtering": False}

def retrieve_results_check(state: dict, config: dict) -> dict:
    return {"is_enough": True, "next_query_aspect": "next query aspect"}

def retrieve_results_check_2(state: dict, config: dict) -> dict:
    if state.get("RetrieveResultsCheck.is_enough") is not None:
        return {"is_enough": True, "next_query_aspect": "next query aspect"}
    return {"is_enough": False, "next_query_aspect": "next query aspect"}

def retrieve_results_check_false(state: dict, config: dict) -> dict:
    return {"is_enough": False, "next_query_aspect": "next query aspect"}

def filter_chunks(state: dict, config: dict) -> dict:
    assert config.get("metadata", {}).get("llm_model") == "gpt-4o"
    return {"filtered_chunks": ["chunk for hello"]}

def final_answer_generation(state: dict, config: dict) -> dict:
    assert state.get("QueryExtender.extended_query") == "extended query"
    assert state.get("Retrieve.chunks") == ["chunk for hello"]
    assert state.get("FilterChunks.filtered_chunks") is None
    assert state.get("Retrieve.chunks") == ["chunk for hello"]
    return {"final_answer": "final answer from chunks"}


def test_awsl_one_cyclerunner_ok():
    FN_MAP = {  
        "query_extender": query_extender,
        "retrieve_from_web": retrieve_from_web,
        "filter_chunks": filter_chunks,
        "final_answer_generation": final_answer_generation,
        "retrieve_results_check": retrieve_results_check,
    }
    result = run_workflow(AWSL_PATH, fn_map=FN_MAP, params={"query": "hello"})
    assert result.get("FinalAnswer.final_answer") == "final answer from chunks"
    assert result.get("RetrieveLoop.iteration_counter") == 1

def test_awsl_two_cycles_runner_ok():
    FN_MAP = {  
        "query_extender": query_extender,
        "retrieve_from_web": retrieve_from_web,
        "filter_chunks": filter_chunks,
        "final_answer_generation": final_answer_generation,
        "retrieve_results_check": retrieve_results_check_2,
    }
    result = run_workflow(AWSL_PATH, fn_map=FN_MAP, params={"query": "hello"})
    assert result.get("FinalAnswer.final_answer") == "final answer from chunks"
    assert result.get("RetrieveLoop.iteration_counter") == 2

def test_awsl_max_iterations_runner_ok():
    FN_MAP = {  
        "query_extender": query_extender,
        "retrieve_from_web": retrieve_from_web,
        "filter_chunks": filter_chunks,
        "final_answer_generation": final_answer_generation,
        "retrieve_results_check": retrieve_results_check_false,
    }
    result = run_workflow(AWSL_PATH, fn_map=FN_MAP, params={"query": "hello"})
    assert result.get("FinalAnswer.final_answer") == "final answer from chunks"
    assert result.get("RetrieveLoop.iteration_counter") == 4




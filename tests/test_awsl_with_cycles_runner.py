from awsl.run_awsl_workflow import run_workflow

AWSL_PATH = "awsl/sample_with_cycle.awsl"

def query_extender(query: str, add_query_aspect: str, config: dict) -> dict:
    return {"extended_query": "extended query"}

def retrieve_from_web(extended_query: str, config: dict) -> dict:
    return {"chunks": ["chunk for hello"], "need_filtering": False}

def retrieve_results_check(chunks: list[str], config: dict) -> dict:
    return {"is_enough": True, "next_query_aspect": "next query aspect"}

def retrieve_results_check_2(chunks: list[str], config: dict) -> dict:
    if len(chunks) > 1:
        return {"is_enough": True, "next_query_aspect": "next query aspect"}
    return {"is_enough": False, "next_query_aspect": "next query aspect"}

def retrieve_results_check_false(chunks: list[str], config: dict) -> dict:
    return {"is_enough": False, "next_query_aspect": "next query aspect"}

def filter_chunks(query: str, need_filtering: bool, chunks: list[str], config: dict) -> dict:
    assert config.get("metadata", {}).get("llm_model") == "gpt-4o"
    return {"filtered_chunks": ["chunk for hello"]}

def final_answer_generation(query: str, 
                            need_filtering: bool, 
                            filtered_chunks: list[str], 
                            retrieved_chunks: list[str], 
                            filtered_chunks_summary: str, 
                            iteration_counter: int,
                            config: dict) -> dict:
    assert query == "hello"
    assert not need_filtering
    assert filtered_chunks is None
    assert retrieved_chunks == ["chunk for hello"]
    assert filtered_chunks_summary is None

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
    assert result.get("RetrieveLoop.iteration_counter") == 0

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




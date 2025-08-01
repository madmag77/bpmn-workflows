from awsl.run_awsl_workflow import run_workflow

AWSL_PATH = "awsl/sample_with_cycle.awsl"


def query_extender(state: dict, config: dict) -> dict:
    return {"extended_query": "extended query"}


def retrieve_from_web(state: dict, config: dict) -> dict:
    return {"chunks": ["chunk for hello"], "need_filtering": False}

def retrieve_results_check(state: dict, config: dict) -> dict:
    return {"is_enough": True, "next_query_aspect": "next query aspect"}

def filter_chunks(state: dict, config: dict) -> dict:
    assert config.get("metadata", {}).get("llm_model") == "gpt-4o"
    return {"filtered_chunks": ["chunk for hello"]}


def final_answer_generation(state: dict, config: dict) -> dict:
    assert state.get("QueryExtender.extended_query") == "extended query"
    assert state.get("Retrieve.chunks") == ["chunk for hello"]
    assert state.get("FilterChunks.filtered_chunks") is None
    assert state.get("Retrieve.chunks") == ["chunk for hello"]
    return {"final_answer": "final answer from chunks"}


FN_MAP = {  
    "query_extender": query_extender,
    "retrieve_from_web": retrieve_from_web,
    "filter_chunks": filter_chunks,
    "final_answer_generation": final_answer_generation,
    "retrieve_results_check": retrieve_results_check,
}


def test_awsl_runner_ok():
    overrides = dict(FN_MAP)
    result = run_workflow(AWSL_PATH, fn_map=overrides, params={"query": "hello"})
    assert result.get("FinalAnswer.final_answer") == "final answer from chunks"



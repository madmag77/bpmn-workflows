from awsl.run_awsl_workflow import run_workflow

AWSL_PATH = "awsl/sample.awsl"


def query_extender(state: dict, config: dict) -> dict:
    return {"extended_query": "extended query"}


def retrieve_from_web(state: dict, config: dict) -> dict:
    return {"chunks": ["chunk for hello"]}


def filter_chunks(state: dict, config: dict) -> dict:
    assert config.get("metadata", {}).get("llm_model") == "gpt-4o"
    return {"filtered_chunks": ["chunk for hello"]}


def final_answer_generation(state: dict, config: dict) -> dict:
    assert state.get("extended_query") == "extended query"
    assert state.get("chunks") == ["chunk for hello"]
    assert state.get("filtered_chunks") == ["chunk for hello"]
    return {"final_answer": "final answer from chunks"}


FN_MAP = {  
    "query_extender": query_extender,
    "retrieve_from_web": retrieve_from_web,
    "filter_chunks": filter_chunks,
    "final_answer_generation": final_answer_generation,
}


def test_awsl_runner_ok():
    overrides = dict(FN_MAP)
    result = run_workflow(AWSL_PATH, fn_map=overrides, params={"query": "hello"})
    assert result.get("final_answer")



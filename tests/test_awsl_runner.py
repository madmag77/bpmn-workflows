from awsl.run_awsl_workflow import run_workflow

AWSL_PATH = "awsl/sample.awsl"


def query_extender(state, config):
    return {"extended_query": "extended query"}


def retrieve_from_web(state, config):
    return {"chunks": ["chunk for hello"]}


def filter_chunks(state, config):
    assert config.get("metadata", {}).get("llm_model") == "gpt-4o"
    return {"filtered_chunks": ["chunk for hello"]}


def final_answer_generation(state, config):
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



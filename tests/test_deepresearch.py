from .helper import run_workflow
import steps.deepresearch_functions as drf

XML_PATH = "workflows/deepresearch/deepresearch.xml"

FN_MAP = {name: getattr(drf, name) for name in dir(drf) if not name.startswith("_")}


def test_deepresearch_ok():
    result = run_workflow(XML_PATH, fn_overrides=FN_MAP, params={"query": "hello"})
    assert result.get("final_answer")


def test_deepresearch_loop():
    def validate(state):
        if state.get("iteration", 0) < 2:
            return {"is_enough": "BAD", "next_query": "next"}
        return {"is_enough": "GOOD", "next_query": ""}

    overrides = dict(FN_MAP)
    overrides["answer_validate"] = validate
    result = run_workflow(XML_PATH, fn_overrides=overrides, params={"query": "hello"})
    assert result.get("final_answer")
    assert result.get("iteration", 0) == 2


def test_deepresearch_max_iterations():
    calls = {k: 0 for k in [
        "query_extender",
        "retrieve_from_web",
        "process_info",
        "answer_validate",
    ]}

    overrides = dict(FN_MAP)

    def wrap(name):
        orig = getattr(drf, name)

        def wrapper(state):
            calls[name] += 1
            return orig(state)

        return wrapper

    for step in ["query_extender", "retrieve_from_web", "process_info"]:
        overrides[step] = wrap(step)

    def always_bad(state):
        calls["answer_validate"] += 1
        return {"is_enough": "BAD", "next_query": "next"}

    overrides["answer_validate"] = always_bad

    result = run_workflow(XML_PATH, fn_overrides=overrides, params={"query": "hello"})
    assert result.get("final_answer")
    assert result.get("iteration", 0) == 10
    for step in calls:
        assert calls[step] == 10

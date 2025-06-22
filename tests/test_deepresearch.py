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

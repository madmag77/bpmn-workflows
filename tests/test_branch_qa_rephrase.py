from .helper import run_workflow

XML_PATH = "examples/example_1/example1.xml"


def eval_relevance(state):
    if state.get("rephraseCount", 0) == 0:
        return {"relevance": "BAD"}
    return {"relevance": "OK"}

def test_branch_qa_rephrase():
    result = run_workflow(XML_PATH, {"evaluate_relevance": eval_relevance})
    assert result["rephraseCount"] == 1
    assert result["relevance"] == "OK"
    assert "answer" in result

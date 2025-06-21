from .helper import run_workflow

XML_PATH = "examples/example_1/example1.xml"


def eval_bad(state):
    return {"relevance": "BAD"}

def test_branch_qa_error():
    result = run_workflow(XML_PATH, {"evaluate_relevance": eval_bad}, params={"rephraseCount": 3})
    assert result.get("relevance") == "BAD"
    assert "answer" in result

from .helper import run_workflow

XML_PATH = "workflows/example_1/example1.xml"


def intent_other(state):
    return {"intent": "not_clear"}


def test_branch_not_clear():
    result = run_workflow(XML_PATH, {"identify_user_intent": intent_other})
    assert result["intent"] == "not_clear"
    assert "query" in result
    assert "answer" in result

from .helper import run_workflow

XML_PATH = "workflows/example_1/example1.xml"


def intent_summarize(state):
    return {"intent": "summarization"}


def test_branch_summarize():
    result = run_workflow(XML_PATH, {"identify_user_intent": intent_summarize})
    assert result["intent"] == "summarization"
    assert "summary" in result
    assert "answer" in result

from .helper import run_workflow

XML_PATH = "workflows/example_1/example1.xml"

def test_branch_qa_ok():
    result = run_workflow(XML_PATH)
    assert result["intent"] == "qa"
    assert result["relevance"] == "OK"
    assert "answer" in result

from typing import Dict, Any, List
from bpmn_ext.bpmn_ext import bpmn_op

@bpmn_op(
    name="analyse_user_query",
    inputs={"query": str},
    outputs={"extended_query": str, "questions": list},
)
def analyse_user_query(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse the user query and decide if clarification is needed."""
    return {
        "extended_query": f"{state.get('query', '')} extended",
        "questions": [],
    }

@bpmn_op(
    name="ask_questions",
    inputs={"questions": list},
    outputs={"clarifications": str},
)
def ask_questions(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"clarifications": "clarified"}

@bpmn_op(
    name="query_extender",
    inputs={"query": str, "clarifications": str, "next_query": str},
    outputs={"extended_query": str},
)
def query_extender(state: Dict[str, Any]) -> Dict[str, Any]:
    state["iteration"] = state.get("iteration", 0) + 1
    return {"extended_query": state.get("next_query") or state.get("query", "")}

@bpmn_op(
    name="retrieve_from_web",
    inputs={"extended_query": str},
    outputs={"chunks": list},
)
def retrieve_from_web(state: Dict[str, Any]) -> Dict[str, Any]:
    q = state.get("extended_query", "")
    return {"chunks": [f"chunk for {q}"]}

@bpmn_op(
    name="process_info",
    inputs={"query": str, "chunks": list, "answer_draft": str},
    outputs={"answer_draft": str},
)
def process_info(state: Dict[str, Any]) -> Dict[str, Any]:
    draft = state.get("answer_draft", "")
    chunks = state.get("chunks", [])
    return {"answer_draft": draft + f" info from {chunks}"}

@bpmn_op(
    name="answer_validate",
    inputs={"answer_draft": str},
    outputs={"is_enough": str, "next_query": str},
)
def answer_validate(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.get("iteration", 0) >= 1:
        return {"is_enough": "GOOD", "next_query": ""}
    return {"is_enough": "BAD", "next_query": "next"}

@bpmn_op(
    name="final_answer_generation",
    inputs={"query": str, "answer_draft": str},
    outputs={"final_answer": str},
)
def final_answer_generation(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"final_answer": state.get("answer_draft", "")}

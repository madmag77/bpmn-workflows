from typing import Dict, Any

from bpmn_ext.bpmn_ext import bpmn_op

@bpmn_op(
    name="identify_user_intent",
    inputs={"input_text": str},
    outputs={"intent": str},
)
def identify_user_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Pretend to analyse the input and return the intent."""
    # For testing return 'qa' always
    return {"intent": "qa"}


@bpmn_op(
    name="ask_user",
    inputs={"question": str},
    outputs={"query": str},
)
def ask_user(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"query": "clarified " + state.get("input_text", "")}


@bpmn_op(
    name="retrieve_financial_documents",
    inputs={"query": str},
    outputs={"chunks": list},
)
def retrieve_financial_documents(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state.get("query", "<none>")
    return {"chunks": [f"chunk for {query}"]}


@bpmn_op(
    name="evaluate_relevance",
    inputs={"chunks": list},
    outputs={"relevance": str},
)
def evaluate_relevance(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"relevance": "OK"}


@bpmn_op(
    name="rephrase_query",
    inputs={"query": str},
    outputs={"new_query": str},
)
def rephrase_query(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state.get("query", "")
    return {"new_query": query + " rephrased"}


@bpmn_op(
    name="increment_counter",
    inputs={"new_query": str, "rephraseCount": int},
    outputs={"rephraseCount": int, "query": str},
)
def increment_counter(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rephraseCount": state.get("rephraseCount", 0) + 1,
        "query": state.get("new_query"),
    }


@bpmn_op(
    name="summarize",
    inputs={"input_text": str},
    outputs={"summary": str},
)
def summarize(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"summary": "summary of " + state.get("input_text", "")}

@bpmn_op(
    name="generate_answer",
    inputs={"source": str},
    outputs={"answer": str},
)
def generate_answer(state: Dict[str, Any]) -> Dict[str, Any]:
    source = state.get("summary") or state.get("chunks")
    return {"answer": f"Answer based on {source}"}

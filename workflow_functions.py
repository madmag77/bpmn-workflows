from typing import Dict, Any

def identify_user_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Pretend to analyse the input and return the intent."""
    # For testing return 'qa' always
    return {"intent": "qa"}


def ask_user(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"query": "clarified " + state.get("input_text", "")}


def retrieve_financial_documents(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state.get("query", "<none>")
    return {"chunks": [f"chunk for {query}"]}


def evaluate_relevance(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"relevance": "OK"}


def rephrase_query(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state.get("query", "")
    return {"new_query": query + " rephrased"}


def increment_counter(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"rephraseCount": state.get("rephraseCount", 0) + 1,
            "query": state.get("new_query")}


def summarize(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"summary": "summary of " + state.get("input_text", "")}


def generate_answer(state: Dict[str, Any]) -> Dict[str, Any]:
    source = state.get("summary") or state.get("chunks")
    return {"answer": f"Answer based on {source}"} 
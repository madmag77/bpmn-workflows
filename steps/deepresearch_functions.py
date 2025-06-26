from typing import Any, Dict
from pathlib import Path
from functools import lru_cache
import yaml
from pydantic import BaseModel, Field
from llama_index.llms.ollama import Ollama
from llama_index.core.llms import ChatMessage
from bpmn_ext.bpmn_ext import bpmn_op
from langgraph.types import interrupt

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "deepresearch.yaml"


class QueryAnalysis(BaseModel):
    extended_query: str = Field(..., description="Revised query for retrieval")
    questions: list[str] = Field(default_factory=list, description="Clarification questions")


class QueryExtension(BaseModel):
    extended_query: str = Field(..., description="Extended query for next iteration")


class AnswerDraft(BaseModel):
    answer_draft: str = Field(..., description="Updated draft answer")


class AnswerValidation(BaseModel):
    is_enough: str = Field(..., description="GOOD if answer is sufficient, BAD otherwise")
    next_query: str = Field("", description="Refined search query if more information is needed")


class FinalAnswer(BaseModel):
    final_answer: str = Field(..., description="Polished final answer")


@lru_cache()
def _load_prompts() -> dict:
    return yaml.safe_load(PROMPT_PATH.read_text())


@lru_cache()
def _base_llm():
    """Return the base LLM instance."""
    return Ollama(model="gemma3:27b")


@lru_cache()
def _structured_llm():
    return _base_llm().as_structured_llm(output_cls=QueryAnalysis)


@lru_cache()
def _structured_llm_extender():
    return _base_llm().as_structured_llm(output_cls=QueryExtension)


@lru_cache()
def _structured_llm_draft():
    return _base_llm().as_structured_llm(output_cls=AnswerDraft)


@lru_cache()
def _structured_llm_validate():
    return _base_llm().as_structured_llm(output_cls=AnswerValidation)


@lru_cache()
def _structured_llm_final():
    return _base_llm().as_structured_llm(output_cls=FinalAnswer)

@bpmn_op(
    name="analyse_user_query",
    inputs={"query": str},
    outputs={"extended_query": str, "questions": list},
)
def analyse_user_query(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse the user query and decide if clarification is needed."""
    query = state.get("query", "")
    prompts = _load_prompts()
    llm = _structured_llm()
    input_msg = ChatMessage.from_str(
        prompts["analyse_user_query"].format(query=query)
    )
    try:
        response = llm.chat([input_msg])
        return response.raw.model_dump()
    except Exception:
        return {
            "extended_query": f"{query} extended",
            "questions": [],
        }

@bpmn_op(
    name="ask_questions",
    inputs={"questions": list},
    outputs={"clarifications": str},
)
def ask_questions(state: Dict[str, Any]) -> Dict[str, Any]:
    questions = state.get("questions", [])
    answer = interrupt({"questions": questions})
    return {"clarifications": answer}

@bpmn_op(
    name="query_extender",
    inputs={"query": str, "clarifications": str, "next_query": str},
    outputs={"extended_query": str},
)
def query_extender(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state.get("query", "")
    clarifications = state.get("clarifications", "")
    next_query = state.get("next_query", "")
    prompts = _load_prompts()
    llm = _structured_llm_extender()
    input_msg = ChatMessage.from_str(
        prompts["query_extender"].format(
            query=query, clarifications=clarifications, next_query=next_query
        )
    )
    try:
        response = llm.chat([input_msg])
        return response.raw.model_dump()
    except Exception:
        parts = []
        if next_query:
            parts.append(next_query)
        if clarifications:
            parts.append(clarifications)
        if query:
            parts.append(query)
        extended = " ".join(parts).strip()
        return {"extended_query": extended}

@bpmn_op(
    name="retrieve_from_web",
    inputs={"extended_query": str},
    outputs={"chunks": list},
)
def retrieve_from_web(state: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve web pages using a headless browser."""
    query = state.get("extended_query", "")
    top_k = int(state.get("top_k", 3))

    try:
        from requests_html import HTMLSession
        from urllib.parse import quote_plus
    except Exception:
        # Fallback behaviour if the dependency is unavailable
        return {"chunks": [f"chunk for {query}"]}

    session = HTMLSession()
    search_url = f"https://www.google.com/search?q={quote_plus(query)}"

    try:
        search_resp = session.get(search_url)
        search_resp.html.render(timeout=20)
    except Exception:
        return {"chunks": [f"chunk for {query}"]}

    links: list[str] = []
    for element in search_resp.html.find("a"):
        href = element.attrs.get("href", "")
        if href.startswith("/url?q="):
            links.append(href.split("/url?q=")[1].split("&")[0])
            if len(links) >= top_k:
                break

    chunks: list[str] = []
    for link in links:
        try:
            page = session.get(link)
            page.html.render(timeout=20)
            if page.html.text:
                chunks.append(page.html.text)
        except Exception:
            continue

    return {"chunks": chunks}


@bpmn_op(
    name="retrieve_from_archive",
    inputs={"extended_query": str},
    outputs={"chunks": list},
)
def retrieve_from_archive(state: Dict[str, Any]) -> Dict[str, Any]:
    """Search archive.org for papers matching the query."""
    query = state.get("extended_query", "")
    limit = int(state.get("top_k", 3))

    try:
        import requests
    except Exception:
        return {"chunks": [f"chunk for {query}"]}

    url = "https://archive.org/advancedsearch.php"
    params = {
        "output": "json",
        "q": query,
        "rows": limit,
        "fields": "title,description",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        docs = data.get("response", {}).get("docs", [])
    except Exception:
        return {"chunks": [f"chunk for {query}"]}

    chunks: list[str] = []
    for doc in docs:
        title = doc.get("title", "")
        desc = doc.get("description", "")
        text = " ".join(part for part in [title, desc] if part).strip()
        if text:
            chunks.append(text)

    return {"chunks": chunks}

@bpmn_op(
    name="process_info",
    inputs={"query": str, "chunks": list, "answer_draft": str},
    outputs={"answer_draft": str},
)
def process_info(state: Dict[str, Any]) -> Dict[str, Any]:
    draft = state.get("answer_draft", "")
    chunks = state.get("chunks", [])
    query = state.get("query", "")
    extended_query = state.get("extended_query", "")
    prompts = _load_prompts()
    llm = _structured_llm_draft()
    joined = "\n".join(chunks)
    input_msg = ChatMessage.from_str(
        prompts["process_info"].format(
            query=query,
            extended_query=extended_query,
            answer_draft=draft,
            chunks=joined,
        )
    )
    try:
        response = llm.chat([input_msg])
        return response.raw.model_dump()
    except Exception:
        return {"answer_draft": draft + f" info from {chunks}"}

@bpmn_op(
    name="answer_validate",
    inputs={"answer_draft": str},
    outputs={"is_enough": str, "next_query": str},
)
def answer_validate(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate if the draft answer satisfies the original query."""
    query = state.get("query", "")
    draft = state.get("answer_draft", "")
    prompts = _load_prompts()
    llm = _structured_llm_validate()
    input_msg = ChatMessage.from_str(
        prompts["answer_validate"].format(query=query, answer_draft=draft)
    )
    try:
        response = llm.chat([input_msg])
        return response.raw.model_dump()
    except Exception:
        if state.get("iteration", 0) >= 1:
            return {"is_enough": "GOOD", "next_query": ""}
        return {"is_enough": "BAD", "next_query": "next"}

@bpmn_op(
    name="final_answer_generation",
    inputs={"query": str, "answer_draft": str},
    outputs={"final_answer": str},
)
def final_answer_generation(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state.get("query", "")
    draft = state.get("answer_draft", "")
    prompts = _load_prompts()
    llm = _structured_llm_final()
    input_msg = ChatMessage.from_str(
        prompts["final_answer_generation"].format(query=query, answer_draft=draft)
    )
    try:
        response = llm.chat([input_msg])
        return response.raw.model_dump()
    except Exception:
        return {"final_answer": draft}

from typing import Any, Dict
from pathlib import Path
from functools import lru_cache
import yaml
from pydantic import BaseModel, Field
from llama_index.llms.ollama import Ollama
from llama_index.core.llms import ChatMessage
from bpmn_ext.bpmn_ext import bpmn_op
from components.web_scraper import search_and_scrape
import logging
import traceback
from langgraph.types import interrupt

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

#from langgraph.types import interrupt

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
    logger.info("Loading prompts from %s", PROMPT_PATH)
    try:
        prompts = yaml.safe_load(PROMPT_PATH.read_text())
        logger.info("Successfully loaded prompts")
        return prompts
    except Exception as e:
        logger.error("Failed to load prompts: %s\n%s", str(e), traceback.format_exc())
        raise


@lru_cache()
def _base_llm():
    """Return the base LLM instance."""
    logger.info("Initializing base LLM")
    try:
        llm = Ollama(model="gemma3:27b", request_timeout=600)
        logger.info("Successfully initialized base LLM")
        return llm
    except Exception as e:
        logger.error("Failed to initialize base LLM: %s\n%s", str(e), traceback.format_exc())
        raise


@lru_cache()
def _structured_llm():
    logger.info("Initializing structured LLM for QueryAnalysis")
    try:
        llm = _base_llm().as_structured_llm(output_cls=QueryAnalysis)
        logger.info("Successfully initialized structured LLM for QueryAnalysis")
        return llm
    except Exception as e:
        logger.error("Failed to initialize structured LLM for QueryAnalysis: %s\n%s", str(e), traceback.format_exc())
        raise


@lru_cache()
def _structured_llm_extender():
    logger.info("Initializing structured LLM for QueryExtension")
    try:
        llm = _base_llm().as_structured_llm(output_cls=QueryExtension)
        logger.info("Successfully initialized structured LLM for QueryExtension")
        return llm
    except Exception as e:
        logger.error("Failed to initialize structured LLM for QueryExtension: %s\n%s", str(e), traceback.format_exc())
        raise


@lru_cache()
def _structured_llm_draft():
    logger.info("Initializing structured LLM for AnswerDraft")
    try:
        llm = _base_llm().as_structured_llm(output_cls=AnswerDraft)
        logger.info("Successfully initialized structured LLM for AnswerDraft")
        return llm
    except Exception as e:
        logger.error("Failed to initialize structured LLM for AnswerDraft: %s\n%s", str(e), traceback.format_exc())
        raise


@lru_cache()
def _structured_llm_validate():
    logger.info("Initializing structured LLM for AnswerValidation")
    try:
        llm = _base_llm().as_structured_llm(output_cls=AnswerValidation)
        logger.info("Successfully initialized structured LLM for AnswerValidation")
        return llm
    except Exception as e:
        logger.error("Failed to initialize structured LLM for AnswerValidation: %s\n%s", str(e), traceback.format_exc())
        raise


@lru_cache()
def _structured_llm_final():
    logger.info("Initializing structured LLM for FinalAnswer")
    try:
        llm = _base_llm().as_structured_llm(output_cls=FinalAnswer)
        logger.info("Successfully initialized structured LLM for FinalAnswer")
        return llm
    except Exception as e:
        logger.error("Failed to initialize structured LLM for FinalAnswer: %s\n%s", str(e), traceback.format_exc())
        raise

@bpmn_op(
    name="analyse_user_query",
    inputs={"query": str},
    outputs={"extended_query": str, "questions": list},
)
def analyse_user_query(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse the user query and decide if clarification is needed."""
    logger.info("Starting analyse_user_query with state: %s", state)
    query = state.get("query", "")
    prompts = _load_prompts()
    llm = _structured_llm()
    input_msg = ChatMessage.from_str(
        prompts["analyse_user_query"].format(query=query)
    )
    try:
        response = llm.chat([input_msg])
        result = response.raw.model_dump()
        logger.info("Successfully completed analyse_user_query: %s", result)
        return result
    except Exception as e:
        logger.error("Error in analyse_user_query: %s\n%s", str(e), traceback.format_exc())
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
    logger.info("Starting ask_questions with state: %s", state)
    try:
        questions = state.get("questions", [])
        if questions:
            answer = interrupt({"questions": questions})
            result = {"clarifications": answer}
            logger.info("Successfully completed ask_questions: %s", result)
        else:
            result = {"clarifications": "no clarifications needed"}
            logger.info("No questions to ask")
        return result
    except Exception as e:
        logger.error("Error in ask_questions: %s\n%s", str(e), traceback.format_exc())
        raise

@bpmn_op(
    name="query_extender",
    inputs={"query": str, "clarifications": str, "next_query": str},
    outputs={"extended_query": str},
)
def query_extender(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Starting query_extender with state: %s", state)
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
        result = response.raw.model_dump()
        logger.info("Successfully completed query_extender: %s", result)
        return result
    except Exception as e:
        logger.error("Error in query_extender: %s\n%s", str(e), traceback.format_exc())
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
    """Retrieve web pages using an undetected headless browser."""
    logger.info("Starting retrieve_from_web with state: %s", state)
    try:
        query = state.get("extended_query", "")
        top_k = int(state.get("top_k", 3))
        result = search_and_scrape(query, top_k)
        logger.info("Successfully completed retrieve_from_web: %s", result)
        return result
    except Exception as e:
        logger.error("Error in retrieve_from_web: %s\n%s", str(e), traceback.format_exc())
        raise

@bpmn_op(
    name="retrieve_from_archive",
    inputs={"extended_query": str},
    outputs={"chunks": list},
)
def retrieve_from_archive(state: Dict[str, Any]) -> Dict[str, Any]:
    """Search archive.org for papers matching the query."""
    logger.info("Starting retrieve_from_archive with state: %s", state)
    query = state.get("extended_query", "")
    limit = int(state.get("top_k", 3))

    try:
        import requests
    except Exception as e:
        logger.error("Failed to import requests: %s", str(e))
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
        
        chunks: list[str] = []
        for doc in docs:
            title = doc.get("title", "")
            desc = doc.get("description", "")
            text = " ".join(part for part in [title, desc] if part).strip()
            if text:
                chunks.append(text)
        
        logger.info("Successfully completed retrieve_from_archive: %s chunks", len(chunks))
        return {"chunks": chunks}
    except Exception as e:
        logger.error("Error in retrieve_from_archive: %s\n%s", str(e), traceback.format_exc())
        return {"chunks": [f"chunk for {query}"]}

@bpmn_op(
    name="process_info",
    inputs={"query": str, "chunks": list, "answer_draft": str},
    outputs={"answer_draft": str},
)
def process_info(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Starting process_info with state: %s", state)
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
        result = response.raw.model_dump()
        logger.info("Successfully completed process_info: %s", result)
        return result
    except Exception as e:
        logger.error("Error in process_info: %s\n%s", str(e), traceback.format_exc())
        return {"answer_draft": draft + f" info from {chunks}"}

@bpmn_op(
    name="answer_validate",
    inputs={"answer_draft": str},
    outputs={"is_enough": str, "next_query": str},
)
def answer_validate(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validate if the draft answer satisfies the original query."""
    logger.info("Starting answer_validate with state: %s", state)
    query = state.get("query", "")
    draft = state.get("answer_draft", "")
    prompts = _load_prompts()
    llm = _structured_llm_validate()
    input_msg = ChatMessage.from_str(
        prompts["answer_validate"].format(query=query, answer_draft=draft)
    )
    try:
        response = llm.chat([input_msg])
        result = response.raw.model_dump()
        logger.info("Successfully completed answer_validate: %s", result)
        return result
    except Exception as e:
        logger.error("Error in answer_validate: %s\n%s", str(e), traceback.format_exc())
        if state.get("iteration", 0) >= 1:
            return {"is_enough": "GOOD", "next_query": ""}
        return {"is_enough": "BAD", "next_query": "next"}

@bpmn_op(
    name="final_answer_generation",
    inputs={"query": str, "answer_draft": str},
    outputs={"final_answer": str},
)
def final_answer_generation(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Starting final_answer_generation with state: %s", state)
    query = state.get("query", "")
    draft = state.get("answer_draft", "")
    prompts = _load_prompts()
    llm = _structured_llm_final()
    input_msg = ChatMessage.from_str(
        prompts["final_answer_generation"].format(query=query, answer_draft=draft)
    )
    try:
        response = llm.chat([input_msg])
        result = response.raw.model_dump()
        logger.info("Successfully completed final_answer_generation: %s", result)
        return result
    except Exception as e:
        logger.error("Error in final_answer_generation: %s\n%s", str(e), traceback.format_exc())
        return {"final_answer": draft}

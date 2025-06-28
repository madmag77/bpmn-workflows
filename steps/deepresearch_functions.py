from typing import Any, Dict
from pathlib import Path
from functools import lru_cache
import yaml
import os
from pydantic import BaseModel, Field
from llama_index.llms.ollama import Ollama
from llama_index.core.llms import ChatMessage
from bpmn_ext.bpmn_ext import bpmn_op
#from langgraph.types import interrupt
from urllib.parse import quote_plus
import undetected_chromedriver as uc
from fake_useragent import UserAgent
from selenium import webdriver
import time
import random

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "deepresearch.yaml"
WEB_SEARCH_URL = os.getenv("WEB_SEARCH_URL")
FILTER_OUT_TAGS = os.getenv("FILTER_OUT_TAGS", "").split(",") if os.getenv("FILTER_OUT_TAGS") else []

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
    #questions = state.get("questions", [])
    #answer = interrupt({"questions": questions})
    return {"clarifications": "Interrested mostly in diagnostics"}

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
    """Retrieve web pages using an undetected headless browser."""
    query = state.get("extended_query", "")
    top_k = int(state.get("top_k", 3))

    ua = UserAgent()
    options = uc.ChromeOptions()
    options.headless = True
    options.add_argument(f'--user-agent={ua.random}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--incognito")
    options.add_argument("--disable-search-engine-choice-screen")
    
    try:
        driver = webdriver.Chrome(options=options)
        
        search_url = f"{WEB_SEARCH_URL}?q={quote_plus(query)}"

        driver.get(search_url)
        time.sleep(random.uniform(2, 4))
        
        links = []
        elements = driver.find_elements("tag name", "a")
        for element in elements:
            href = element.get_attribute("href")
            if href and all(tag not in href for tag in FILTER_OUT_TAGS): 
                links.append(href)
                if len(links) >= top_k:
                    break
                    
        chunks = []
        for link in links:
            try:
                driver.get(link)
                time.sleep(random.uniform(2, 5))
                
                page_text = driver.find_element("tag name", "body").text
                if page_text:
                    # Clean and normalize the text
                    text = " ".join(page_text.split())
                    if len(text) > 100:  # Only keep substantial content
                        chunks.append(text[:10000])  # Limit chunk size
            except Exception as e:
                print(f"Failed to fetch {link}: {str(e)}")
                continue
                
        if not chunks:
            chunks = [f"No valid content could be retrieved for: {query}. Please try a different search query."]
            
        return {"chunks": chunks}
        
    except Exception as e:
        print(f"Browser automation failed: {str(e)}")
        # Fallback to a simple response if browser automation fails
        return {"chunks": [f"Unable to retrieve search results for: {query}. Please try again later."]}
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


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

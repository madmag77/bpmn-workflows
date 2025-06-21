from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any

from bpmn_workflows import compat  # noqa: F401
from langgraph.graph import StateGraph, END

# --- Stub functions used by the example workflow ---

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


# --- BPMN Parsing -----------------------------------------------------------

NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "camunda": "http://camunda.org/schema/1.0/bpmn",
}


def parse_bpmn(path: str):
    """Parse BPMN XML returning nodes and flows."""
    tree = ET.parse(path)
    root = tree.getroot()

    nodes: Dict[str, Dict[str, Any]] = {}
    for tag, typ in [
        ("serviceTask", "serviceTask"),
        ("exclusiveGateway", "exclusiveGateway"),
        ("startEvent", "startEvent"),
        ("endEvent", "endEvent"),
    ]:
        for el in root.findall(f".//bpmn:{tag}", NS):
            info: Dict[str, Any] = {"type": typ}
            if typ == "serviceTask":
                expr = el.attrib.get(f"{{{NS['camunda']}}}expression", "")
                m = re.search(r"\${(\w+)", expr)
                info["fn"] = m.group(1) if m else None
            nodes[el.attrib["id"]] = info

    flows = []
    for sf in root.findall(".//bpmn:sequenceFlow", NS):
        cond_el = sf.find("bpmn:conditionExpression", NS)
        cond_text = cond_el.text.strip() if cond_el is not None and cond_el.text else None
        flows.append({
            "source": sf.attrib["sourceRef"],
            "target": sf.attrib["targetRef"],
            "condition": cond_text,
            "default": sf.attrib.get("default") == "true",
        })
    return nodes, flows


# --- LangGraph Construction -------------------------------------------------

def make_task(fn_name: str):
    def task(state: Dict[str, Any]) -> Dict[str, Any]:
        func = globals().get(fn_name)
        if callable(func):
            update = func(state) or {}
            state.update(update)
        return state
    return task


def make_router(flows):
    def router(state: Dict[str, Any]):
        default_target = None
        for fl in flows:
            if fl["default"]:
                default_target = fl["target"]
        for fl in flows:
            expr = fl["condition"]
            if expr:
                cond = expr
                if cond.startswith("${") and cond.endswith("}"):
                    cond = cond[2:-1]
                cond = cond.replace("&&", "and").replace("||", "or")
                try:
                    if eval(cond, {}, state):
                        return fl["target"]
                except Exception:
                    pass
        return default_target or flows[0]["target"]
    return router


def build_graph(xml_path: str):
    nodes, flows = parse_bpmn(xml_path)
    outgoing: Dict[str, list] = {}
    for fl in flows:
        outgoing.setdefault(fl["source"], []).append(fl)

    graph = StateGraph(dict)
    for node_id, info in nodes.items():
        if info["type"] == "serviceTask":
            graph.add_node(node_id, make_task(info.get("fn")))
        else:
            graph.add_node(node_id, lambda state: state)

    # add edges excluding gateways which are handled separately
    for fl in flows:
        if nodes.get(fl["source"], {}).get("type") == "exclusiveGateway":
            continue
        if fl["condition"] or fl["default"]:
            continue
        graph.add_edge(fl["source"], fl["target"])

    # gateways as conditional edges
    for node_id, info in nodes.items():
        if info["type"] == "exclusiveGateway":
            router = make_router(outgoing.get(node_id, []))
            graph.add_conditional_edges(node_id, router)

    starts = [k for k, v in nodes.items() if v["type"] == "startEvent"]
    ends = [k for k, v in nodes.items() if v["type"] == "endEvent"]
    if not starts or not ends:
        raise ValueError("Workflow must have start and end events")
    graph.set_entry_point(starts[0])
    graph.set_finish_point(ends[0])
    return graph.compile()


if __name__ == "__main__":
    app = build_graph("examples/example_1/example1.xml")
    result = app.invoke({"input_text": "hello", "rephraseCount": 0})
    print(result)

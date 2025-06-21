from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any
import argparse

from bpmn_workflows import compat  # noqa: F401
from langgraph.graph import StateGraph, END

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
        cond_text = None
        if cond_el is not None and cond_el.text:
            cond_text = cond_el.text.strip()
            if cond_text.startswith("\\${"):
                cond_text = cond_text[1:]
        flows.append({
            "source": sf.attrib["sourceRef"],
            "target": sf.attrib["targetRef"],
            "condition": cond_text,
            "default": sf.attrib.get("default") == "true",
        })
    return nodes, flows


# --- LangGraph Construction -------------------------------------------------

def make_task(fn_name: str, fn_map: Dict[str, Any]):
    """Wrap a function from *fn_map* so it can be used in the graph."""

    def task(state: Dict[str, Any]) -> Dict[str, Any]:
        func = fn_map.get(fn_name)
        if not callable(func):
            raise ValueError(f"Function '{fn_name}' not provided")
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


def build_graph(xml_path: str, functions: Dict[str, Any]):
    nodes, flows = parse_bpmn(xml_path)
    outgoing: Dict[str, list] = {}
    for fl in flows:
        outgoing.setdefault(fl["source"], []).append(fl)

    fn_map = functions
    graph = StateGraph(dict)
    for node_id, info in nodes.items():
        if info["type"] == "serviceTask":
            graph.add_node(node_id, make_task(info.get("fn"), fn_map))
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
    parser = argparse.ArgumentParser(description="Run a BPMN workflow.")
    parser.add_argument("workflow_path", type=str, help="Path to the workflow XML file")
    parser.add_argument(
        "--param", action="append", default=[],
        help="Workflow input parameter in key=value format. Can be used multiple times."
    )
    args = parser.parse_args()

    import workflow_functions  # Import all workflow functions
    fn_map = {
        k: getattr(workflow_functions, k)
        for k in dir(workflow_functions)
        if not k.startswith("_")
    }

    def parse_params(param_list):
        params = {}
        for p in param_list:
            if "=" not in p:
                raise ValueError(f"Invalid param: {p}. Must be key=value.")
            k, v = p.split("=", 1)
            # Try to convert to int or float if possible
            if v.isdigit():
                v = int(v)
            else:
                try:
                    v = float(v)
                except ValueError:
                    pass
            params[k] = v
        return params

    app = build_graph(args.workflow_path, functions=fn_map)
    input_kwargs = parse_params(args.param)
    result = app.invoke(input_kwargs)
    print(result)

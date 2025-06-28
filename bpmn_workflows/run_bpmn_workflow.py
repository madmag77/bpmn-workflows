from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, Tuple, Set
import argparse
import json
from langgraph.types import Command
import importlib
from bpmn_workflows import compat  # noqa: F401
from langgraph.graph import StateGraph

# --- BPMN Parsing -----------------------------------------------------------

NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "camunda": "http://camunda.org/schema/1.0/bpmn",
}


def parse_bpmn(path: str):
    """Parse BPMN XML returning nodes, flows and loop metadata."""
    tree = ET.parse(path)
    root = tree.getroot()

    loops: Dict[str, int] = {}
    node_to_sp: Dict[str, str] = {}
    for sp in root.findall(".//bpmn:subProcess", NS):
        mi = sp.find("bpmn:multiInstanceLoopCharacteristics", NS)
        if mi is not None and mi.attrib.get("isSequential") == "true":
            card_el = mi.find("bpmn:loopCardinality", NS)
            if card_el is not None and card_el.text:
                loops[sp.attrib["id"]] = int(card_el.text)
            for el in sp.findall(".//*", NS):
                if "id" in el.attrib:
                    node_to_sp[el.attrib["id"]] = sp.attrib["id"]

    nodes: Dict[str, Dict[str, Any]] = {}
    for tag, typ in [
        ("serviceTask", "serviceTask"),
        ("exclusiveGateway", "exclusiveGateway"),
        ("startEvent", "startEvent"),
        ("endEvent", "endEvent"),
        ("subProcess", "subProcess"),
    ]:
        for el in root.findall(f".//bpmn:{tag}", NS):
            info: Dict[str, Any] = {"type": typ}
            if typ == "serviceTask":
                expr = el.attrib.get(f"{{{NS['camunda']}}}expression", "")
                m = re.search(r"\${(\w+)", expr)
                info["fn"] = m.group(1) if m else None
            nodes[el.attrib["id"]] = info

    gw_defaults = {
        gw.attrib.get("default"): True
        for gw in root.findall(".//bpmn:exclusiveGateway", NS)
        if gw.attrib.get("default")
    }

    flows = []
    for sf in root.findall(".//bpmn:sequenceFlow", NS):
        cond_el = sf.find("bpmn:conditionExpression", NS)
        cond_text = None
        if cond_el is not None and cond_el.text:
            cond_text = cond_el.text.strip()
            if cond_text.startswith("\\${"):
                cond_text = cond_text[1:]
        is_default = sf.attrib.get("default") == "true" or gw_defaults.get(sf.attrib.get("id"))
        flows.append({
            "source": sf.attrib["sourceRef"],
            "target": sf.attrib["targetRef"],
            "condition": cond_text,
            "default": bool(is_default),
        })

    start_nodes: Dict[str, Set[str]] = {sp: set() for sp in loops}
    for fl in flows:
        sp_id = node_to_sp.get(fl["source"])
        if sp_id and nodes.get(fl["source"], {}).get("type") == "startEvent":
            start_nodes[sp_id].add(fl["target"])

    loop_flows: Set[Tuple[str, str]] = set()
    for fl in flows:
        sp_id = node_to_sp.get(fl["source"])
        if sp_id and sp_id == node_to_sp.get(fl["target"]):
            if fl["target"] in start_nodes.get(sp_id, set()):
                loop_flows.add((fl["source"], fl["target"]))

    return nodes, flows, loops, node_to_sp, loop_flows, start_nodes


# --- LangGraph Construction -------------------------------------------------

def make_task(node_id: str, fn_name: str, fn_map: Dict[str, Any], start_nodes, node_to_sp):
    """Wrap a function from *fn_map* so it can be used in the graph."""

    def task(state: Dict[str, Any]) -> Dict[str, Any]:
        sp_id = node_to_sp.get(node_id)
        if sp_id and node_id in start_nodes.get(sp_id, set()):
            key = f"{sp_id}_iteration"
            state[key] = state.get(key, 0) + 1
            state["iteration"] = state[key]
        func = fn_map.get(fn_name)
        if not callable(func):
            raise ValueError(f"Function '{fn_name}' not provided")
        update = func(state) or {}
        state.update(update)
        return state

    return task


def make_router(node_id: str, flows, loops, node_to_sp, loop_flows):
    def router(state: Dict[str, Any]):
        default_target = None
        for fl in flows:
            if fl["default"]:
                default_target = fl["target"]
        chosen = None
        for fl in flows:
            expr = fl["condition"]
            if expr:
                cond = expr
                if cond.startswith("${") and cond.endswith("}"):
                    cond = cond[2:-1]
                cond = cond.replace("&&", "and").replace("||", "or")
                try:
                    if eval(cond, {}, state):
                        chosen = fl["target"]
                        break
                except Exception:
                    pass
        if chosen is None:
            chosen = default_target or flows[0]["target"]

        sp_id = node_to_sp.get(node_id)
        if sp_id and (node_id, chosen) in loop_flows:
            key = f"{sp_id}_iteration"
            count = state.get(key, 0) + 1
            if count > loops.get(sp_id, count):
                for fl in flows:
                    if (node_id, fl["target"]) not in loop_flows:
                        chosen = fl["target"]
                        break
            else:
                state[key] = count
                state["iteration"] = count

        return chosen
    return router


def build_graph(
    xml_path: str,
    functions: Dict[str, Any],
    checkpointer: Any | None = None,
):
    nodes, flows, loops, node_to_sp, loop_flows, start_nodes = parse_bpmn(xml_path)
    outgoing: Dict[str, list] = {}
    for fl in flows:
        outgoing.setdefault(fl["source"], []).append(fl)

    fn_map = functions
    graph = StateGraph(dict)
    for node_id, info in nodes.items():
        if info["type"] == "serviceTask":
            graph.add_node(node_id, make_task(node_id, info.get("fn"), fn_map, start_nodes, node_to_sp))
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
            router = make_router(node_id, outgoing.get(node_id, []), loops, node_to_sp, loop_flows)
            graph.add_conditional_edges(node_id, router)

    starts = [k for k, v in nodes.items() if v["type"] == "startEvent"]
    ends = [k for k, v in nodes.items() if v["type"] == "endEvent"]
    if not starts or not ends:
        raise ValueError("Workflow must have start and end events")
    graph.set_entry_point(starts[0])
    graph.set_finish_point(ends[0])
    return graph.compile(checkpointer=checkpointer)

def run_workflow(workflow_path: str, 
                 fn_map=None, 
                 params: dict[str, Any] | None = None, 
                 thread_id: str | None = None, 
                 resume: str | None = None, 
                 checkpointer: Any | None = None):
    app = build_graph(workflow_path, functions=fn_map, checkpointer=checkpointer)
    #print(app.get_graph().draw_ascii())
    config: Dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    if resume:
        resume_val = json.loads(resume)
        result = app.invoke(Command(resume=resume_val), config)
    else:
        input_kwargs = params
        result = app.invoke(input_kwargs, config)
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a BPMN workflow.")
    parser.add_argument("workflow_path", type=str, help="Path to the workflow XML file")
    parser.add_argument(
        "--functions",
        type=str,
        default="steps.example_functions",
        help="Python module containing the workflow functions (default: steps.example_functions)"
    )
    parser.add_argument(
        "--param", action="append", default=[],
        help="Workflow input parameter in key=value format. Can be used multiple times."
    )
    parser.add_argument(
        "--thread-id",
        type=str,
        default="cli",
        help="Thread identifier for resuming workflows",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="JSON encoded value used to resume an interrupted workflow",
    )
    args = parser.parse_args()

    mod = importlib.import_module(args.functions)
    fn_map = {
        k: getattr(mod, k)
        for k in dir(mod)
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

    # TODO: add default checkpointer
    result = run_workflow(args.workflow_path, fn_map, parse_params(args.param), args.thread_id, args.resume)
    print(result)

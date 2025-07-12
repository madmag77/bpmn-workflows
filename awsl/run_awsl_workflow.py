# Runner for AWsl workflows

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json
import argparse

from lark import Lark, Transformer
from langgraph.graph import StateGraph
from langgraph.types import Command


def load_grammar() -> str:
    return (Path(__file__).with_name("awsl.bnf")).read_text()


class ASTBuilder(Transformer):
    def workflow(self, items):
        name = items[0]
        body = items[1]
        wf = {"name": name, "inputs": {}, "outputs": [], "steps": []}
        for it in body:
            if isinstance(it, dict) and it.get("type") == "inputs":
                wf["inputs"] = it["params"]
            elif isinstance(it, dict) and it.get("type") == "outputs":
                wf["outputs"] = it["params"]
            elif isinstance(it, dict) and it.get("type") != "metadata":
                wf["steps"].append(it)
        return wf

    def workflow_body(self, items):
        return items

    def metadata_block(self, items):
        return {"type": "metadata"}

    def inputs_block(self, items):
        params = {}
        for typ, name, expr in items:
            if expr is None:
                params[name] = name
            else:
                params[name] = expr
        return {"type": "inputs", "params": params}

    def outputs_block(self, items):
        return {"type": "outputs", "params": [name for _, name, _ in items]}

    def param_decl(self, items):
        if len(items) == 3:
            return items[0], items[1], items[2]
        return items[0], items[1], None

    def node_block(self, items):
        name = items[0]
        body = items[1]
        node = {"type": "node", "name": name, "call": body["call"], "when": body.get("when"), "inputs": body.get("inputs", {}), "hitl": body.get("hitl")}
        return node

    def node_body(self, items):
        info = {"call": items[0]}
        for it in items[1:]:
            info.update(it)
        return info

    def node_element(self, items):
        # unwrap single element rules
        return items[0]

    def call_stmt(self, items):
        return items[0]

    def when_clause(self, items):
        return {"when": items[0]}

    def hitl_block(self, items):
        return {"hitl": True}

    def cycle_block(self, items):
        name = items[0]
        body = items[1]
        info = {
            "type": "cycle",
            "name": name,
            "inputs": body.get("inputs", {}),
            "outputs": body.get("outputs", []),
            "nodes": body.get("nodes", []),
            "guard": body["guard"],
            "max_iterations": body["max_iterations"],
        }
        return info

    def cycle_body(self, items):
        res = {"inputs": {}, "outputs": [], "nodes": []}
        for it in items:
            if isinstance(it, dict) and it.get("type") == "node":
                res["nodes"].append(it)
            elif isinstance(it, dict) and it.get("type") == "inputs":
                res["inputs"] = it["params"]
            elif isinstance(it, dict) and it.get("type") == "outputs":
                res["outputs"] = it["params"]
            elif isinstance(it, dict) and "guard" in it:
                res["guard"] = it["guard"]
            elif isinstance(it, int):
                res["max_iterations"] = it
        return res

    def guard_clause(self, items):
        return {"guard": items[0]}

    def expr(self, items):
        text = str(items[0]).strip()
        if "#" in text:
            text = text.split("#", 1)[0].strip()
        return text

    def INT(self, token):
        return int(token)

    def NAME(self, token):
        return str(token)

    def STRING(self, token):
        s = str(token)
        return s[1:-1]

    def DURATION(self, token):
        return str(token)


class _Noop:
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {}


def _eval_value(expr: str, state: Dict[str, Any]):
    if expr is None:
        return None
    expr = str(expr).strip()
    if expr.startswith("\"") and expr.endswith("\""):
        return expr[1:-1]
    try:
        return int(expr)
    except ValueError:
        try:
            return float(expr)
        except ValueError:
            pass
    if "." in expr:
        _, field = expr.split(".", 1)
        return state.get(field)
    return state.get(expr)


def _eval_condition(expr: str, state: Dict[str, Any]) -> bool:
    if expr is None:
        return True
    expr = str(expr).strip()
    import re
    if any(op in expr for op in ["&&", "||", "==", "!=", " and ", " or ", "<", ">"]):
        expr_py = re.sub(r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)", lambda m: f"state.get('{m.group(2)}')", expr)
        expr_py = re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\b", lambda m: f"state.get('{m.group(0)}')", expr_py)
        try:
            return bool(eval(expr_py, {"state": state}))
        except Exception:
            return False
    else:
        val = _eval_value(expr, state)
        if isinstance(val, str):
            return val.upper() == "GOOD"
        return bool(val)


def make_task(fn_name: str, fn_map: Dict[str, Any], when: str | None = None):
    def task(state: Dict[str, Any]) -> Dict[str, Any]:
        if when and not _eval_condition(when, state):
            return state
        func = fn_map.get(fn_name)
        if not callable(func):
            raise ValueError(f"Function '{fn_name}' not provided")
        update = func(state) or {}
        state.update(update)
        return state

    return task


def make_setter(assignments: Dict[str, str]):
    def setter(state: Dict[str, Any]) -> Dict[str, Any]:
        for k, expr in assignments.items():
            val = _eval_value(expr, state)
            if val is not None:
                state[k] = val
        return state

    return setter


def make_cycle_router(name: str, guard: str, start_node: str, max_iterations: int):
    iteration_key = f"{name}_iteration"

    def router(state: Dict[str, Any]):
        count = state.get(iteration_key, 0) + 1
        state[iteration_key] = count
        state["iteration"] = count
        # debug print can be removed later
        # print(f"cycle {name} iteration {count} guard={_eval_condition(guard, state)}")
        if _eval_condition(guard, state) or count >= max_iterations:
            return f"{name}_exit"
        return start_node

    return router


def parse_awsl(path: str):
    grammar = load_grammar()
    parser = Lark(grammar, start="workflow")
    tree = parser.parse(Path(path).read_text())
    transformer = ASTBuilder()
    return transformer.transform(tree)


def build_graph(path: str, functions: Dict[str, Any], checkpointer: Any | None = None):
    ast = parse_awsl(path)
    fn_map = dict(functions)
    fn_map.setdefault("noop", _Noop())

    graph = StateGraph(dict)
    prev_external = None
    entry = None

    for step in ast["steps"]:
        if step["type"] == "node":
            graph.add_node(step["name"], make_task(step["call"], fn_map, step.get("when")))
            if prev_external:
                graph.add_edge(prev_external, step["name"])
            else:
                entry = step["name"]
            prev_external = step["name"]
        elif step["type"] == "cycle":
            init_name = f"{step['name']}_init"
            graph.add_node(init_name, make_setter(step.get("inputs", {})))
            if prev_external:
                graph.add_edge(prev_external, init_name)
            else:
                entry = init_name
            first_internal = None
            prev = None
            for node in step["nodes"]:
                graph.add_node(node["name"], make_task(node["call"], fn_map, node.get("when")))
                if prev:
                    graph.add_edge(prev, node["name"])
                prev = node["name"]
                if first_internal is None:
                    first_internal = node["name"]
            exit_name = f"{step['name']}_exit"
            graph.add_node(exit_name, lambda s: s)
            router = make_cycle_router(step['name'], step['guard'], first_internal, step['max_iterations'])
            graph.add_conditional_edges(prev, router)
            graph.add_edge(init_name, first_internal)
            prev_external = exit_name
        else:
            continue

    graph.set_entry_point(entry)
    graph.set_finish_point(prev_external)
    return graph.compile(checkpointer=checkpointer)


def run_workflow(workflow_path: str,
                 fn_map=None,
                 params: Dict[str, Any] | None = None,
                 thread_id: str | None = None,
                 resume: str | None = None,
                 checkpointer: Any | None = None):
    app = build_graph(workflow_path, functions=fn_map, checkpointer=checkpointer)
    config: Dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    if resume:
        resume_val = json.loads(resume)
        result = app.invoke(Command(resume=resume_val), config)
    else:
        result = app.invoke(params or {}, config)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an AWsl workflow.")
    parser.add_argument("workflow_path", type=str, help="Path to the workflow file")
    parser.add_argument("--functions", type=str, default="steps.deepresearch_functions",
                        help="Python module containing the workflow functions")
    parser.add_argument("--param", action="append", default=[],
                        help="Workflow input parameter key=value")
    parser.add_argument("--thread-id", type=str, default="cli")
    parser.add_argument("--resume", type=str, default=None)
    args = parser.parse_args()

    mod = __import__(args.functions, fromlist=["*"])
    fn_map = {k: getattr(mod, k) for k in dir(mod) if not k.startswith("_")}

    def parse_params(param_list: List[str]):
        out = {}
        for p in param_list:
            if "=" not in p:
                raise ValueError(f"Invalid param: {p}")
            k, v = p.split("=", 1)
            if v.isdigit():
                v = int(v)
            else:
                try:
                    v = float(v)
                except ValueError:
                    pass
            out[k] = v
        return out

    params = parse_params(args.param)
    result = run_workflow(args.workflow_path, fn_map, params, args.thread_id, args.resume)
    print(result)

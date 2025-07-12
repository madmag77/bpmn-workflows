# Runner for AWsl workflows

from __future__ import annotations
import json
from typing import Any, Dict, List, Set
import argparse

from langgraph.graph import StateGraph
from langgraph.types import Command

from .grammar.workflow_parser import parse_awsl_to_objects, print_workflow_structure, NodeClass, CycleClass


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
        expr_py = re.sub(r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)", 
                         lambda m: f"state.get('{m.group(2)}')", expr)
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


def extract_dependencies(inputs: List, workflow_inputs: Set[str]) -> Set[str]:
    """Extract node dependencies from input assignments"""
    dependencies = set()
    for inp in inputs:
        if inp.default_value is not None:
            default_val = str(inp.default_value).strip()
            # Check if it's a node reference (contains a dot)
            if "." in default_val and not default_val.startswith('"'):
                node_name = default_val.split(".")[0]
                # Only add as dependency if it's not a workflow input
                if node_name not in workflow_inputs:
                    dependencies.add(node_name)
    return dependencies


def build_graph(path: str, functions: Dict[str, Any], checkpointer: Any | None = None, debug: bool = False):
    ast = parse_awsl_to_objects(path)
    fn_map = dict(functions)
    fn_map.setdefault("noop", _Noop())

    graph = StateGraph(dict)
    
    # Get workflow input names
    workflow_inputs = {inp.name for inp in ast.inputs}
    
    # Collect all nodes and their dependencies
    all_nodes = {}
    node_dependencies = {}
    entry_points = []
    
    if debug:
        print("=== DEBUG: Node Dependencies ===")
    
    for step in ast.steps:
        if isinstance(step, NodeClass):
            all_nodes[step.name] = step
            deps = extract_dependencies(step.inputs, workflow_inputs)
            node_dependencies[step.name] = deps
            
            if debug:
                print(f"Node {step.name}: dependencies = {deps}")
            
            # Add node to graph
            graph.add_node(step.name, make_task(step.call, fn_map, step.when))
            
            # If no dependencies, it's an entry point
            if not deps:
                entry_points.append(step.name)
                
        elif isinstance(step, CycleClass):
            # Handle cycle as a composite node
            init_name = f"{step.name}_init"
            exit_name = f"{step.name}_exit"
            
            # Add cycle init node
            inputs_dict = {inp.name: inp.default_value for inp in step.inputs if inp.default_value is not None}
            graph.add_node(init_name, make_setter(inputs_dict))
            
            # Extract dependencies for the cycle
            deps = extract_dependencies(step.inputs, workflow_inputs)
            node_dependencies[init_name] = deps
            all_nodes[init_name] = step
            
            if debug:
                print(f"Cycle {step.name} (init): dependencies = {deps}")
            
            # If no dependencies, it's an entry point
            if not deps:
                entry_points.append(init_name)
            
            # Add internal cycle nodes
            first_internal = None
            prev = None
            for node in step.nodes:
                graph.add_node(node.name, make_task(node.call, fn_map, node.when))
                if prev:
                    graph.add_edge(prev, node.name)
                prev = node.name
                if first_internal is None:
                    first_internal = node.name
            
            # Add cycle exit node and router
            graph.add_node(exit_name, lambda s: s)
            router = make_cycle_router(step.name, step.guard, first_internal, step.max_iterations)
            graph.add_conditional_edges(prev, router)
            graph.add_edge(init_name, first_internal)
            
            # Track the cycle as a unit (using init node as representative)
            all_nodes[step.name] = step
            # Don't add cycle name to node_dependencies - only init_name should be there
    
    if debug:
        print(f"Entry points: {entry_points}")
        print("=== Creating dependency edges ===")
    
    # Create dependency-based edges
    for node_name, deps in node_dependencies.items():
        for dep in deps:
            # Handle cycle dependencies
            if dep in all_nodes and isinstance(all_nodes[dep], CycleClass):
                # Connect to cycle's exit node
                if debug:
                    print(f"Adding edge: {dep}_exit -> {node_name}")
                graph.add_edge(f"{dep}_exit", node_name)
            elif dep in all_nodes:
                # Regular node dependency
                if debug:
                    print(f"Adding edge: {dep} -> {node_name}")
                graph.add_edge(dep, node_name)
    
    # Set entry points
    if len(entry_points) == 1:
        graph.set_entry_point(entry_points[0])
    elif len(entry_points) > 1:
        # Multiple entry points - need to handle this case
        # For now, just pick the first one
        graph.set_entry_point(entry_points[0])
    else:
        # No entry points found - fallback to first node
        if ast.steps:
            first_step = ast.steps[0]
            if isinstance(first_step, NodeClass):
                graph.set_entry_point(first_step.name)
            elif isinstance(first_step, CycleClass):
                graph.set_entry_point(f"{first_step.name}_init")
    
    # Find terminal nodes (nodes with no outgoing edges) for finish point
    terminal_nodes = []
    for step in ast.steps:
        if isinstance(step, NodeClass):
            # Check if this node is a dependency for any other node
            is_dependency = any(step.name in deps for deps in node_dependencies.values())
            if not is_dependency:
                terminal_nodes.append(step.name)
        elif isinstance(step, CycleClass):
            # Check if this cycle is a dependency for any other node  
            is_dependency = any(step.name in deps for deps in node_dependencies.values())
            if not is_dependency:
                terminal_nodes.append(f"{step.name}_exit")
    
    # Set finish point
    if terminal_nodes:
        graph.set_finish_point(terminal_nodes[0])
    
    compiled_graph = graph.compile(checkpointer=checkpointer)
    
    if debug:
        print("\n=== COMPILED GRAPH ===")
        print(compiled_graph.get_graph().draw_mermaid())
    
    return compiled_graph


def run_workflow(workflow_path: str,
                 fn_map=None,
                 params: Dict[str, Any] | None = None,
                 thread_id: str | None = None,
                 resume: str | None = None,
                 checkpointer: Any | None = None,
                 debug: bool = False):
    app = build_graph(workflow_path, functions=fn_map, checkpointer=checkpointer, debug=debug)
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
    parser.add_argument("--print-structure", action="store_true", 
                        help="Print the workflow object structure and exit")
    parser.add_argument("--debug", action="store_true", 
                        help="Print debug information including dependency graph")
    args = parser.parse_args()

    if args.print_structure:
        workflow = parse_awsl_to_objects(args.workflow_path)
        print_workflow_structure(workflow)
        exit(0)

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
    result = run_workflow(args.workflow_path, fn_map, params, args.thread_id, args.resume, debug=args.debug)
    print(result)

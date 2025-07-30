# Runner for AWsl workflows

from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Set, Type
import argparse
from typing_extensions import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, RunnableConfig

from .grammar.workflow_parser import parse_awsl_to_objects, print_workflow_structure, NodeClass, CycleClass, Workflow

START_NODE_NAME = "START_NODE"
NOOP_NODE_NAME = "NOOP_NODE"

def reducer(a: Any, b: Any) -> Any:
    return b or a

PropertyType = Annotated[Any | None, reducer]

def _eval_value(expr: str, state: Dict[str, Any]):
    if expr is None:
        raise ValueError("Value is None")
    
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
    # if "." in expr:
    #     _, field = expr.split(".", 1)
    #     return state.get(field)
    return state.get(expr)


def _eval_condition(expr: str, state: Dict[str, Any]) -> bool:
    if expr is None:
        raise ValueError("Condition is None")
    
    expr = str(expr).strip()
    # Replace variable names in the expression with their corresponding values from state
    def repl(match):
        key = match.group(0)
        if key in state:
            return repr(state[key])
        return "False"
    expr_py = re.sub(r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)", repl, expr)
    return bool(eval(expr_py))

def make_task(node: NodeClass, fn_map: Dict[str, Any], graphStateType: Type):
    func = fn_map.get(node.call)
    if not callable(func):
        raise ValueError(f"Function '{node.call}' not provided")
    
    def task(state: graphStateType, config: RunnableConfig) -> graphStateType:
        all_inputs_available = all(state.get(inp.default_value) is not None 
                                   for inp in node.inputs if not inp.optional and inp.default_value is not None)
        if not all_inputs_available:
            return Command(goto=NOOP_NODE_NAME)
    
        if node.when and not _eval_condition(node.when, state):
            return Command(goto=NOOP_NODE_NAME)
        
        metadata = config.get("metadata", {})
        metadata.update({constant.name: constant.value for constant in node.constants})
        update = func(state, config = dict(config, **{"metadata": metadata})) or {}
        update_with_node_name = {node.name + "." + k: v for k, v in update.items()}
        return update_with_node_name

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
                dependencies.add(node_name)
            elif default_val in workflow_inputs:
                dependencies.add(START_NODE_NAME)
            else:
                raise ValueError(f"Node {default_val} not found")
    return dependencies


def build_graph(path: str, functions: Dict[str, Any], checkpointer: Any | None = None, debug: bool = False):
    workflow: Workflow = parse_awsl_to_objects(path)
    
    # Dynamically build fields from workflow inputs, outputs, and all node inputs/outputs
    field_names = set()
    
    # Add workflow inputs and outputs
    for inp in workflow.inputs:
        field_names.add(inp.name)
    for out in workflow.outputs:
        field_names.add(out.name)
    
    for node in workflow.nodes:
        if isinstance(node, NodeClass):
            for out in node.outputs:
                field_names.add(node.name + "." + out.name)
        elif isinstance(node, CycleClass):
            for out in node.outputs:
                field_names.add(node.name + "." + out.name)
            for cycle_node in node.nodes:
                for out in cycle_node.outputs:
                    field_names.add(node.name + "." + out.name)
    
    # Build the new_fields dictionary
    new_fields = {field_name: PropertyType for field_name in field_names}
    graphStateType = TypedDict('GraphState', new_fields)

    def _Noop(state: graphStateType, config: RunnableConfig) -> graphStateType:
        return {}

    fn_map = dict(functions)
    fn_map.setdefault("noop", _Noop)

    graph = StateGraph(graphStateType)
    
    # Get workflow input names
    workflow_inputs = {inp.name for inp in workflow.inputs}
    
    # Collect all nodes and their dependencies
    all_nodes = {}
    node_dependencies = {}
    all_dependencies = set()
     # Add dummy start node
    graph.add_node(START_NODE_NAME, _Noop)
    graph.add_edge(START, START_NODE_NAME)
    all_nodes[START_NODE_NAME] = _Noop
    graph.add_node(NOOP_NODE_NAME, _Noop)

    if debug:
        print("=== DEBUG: Node Dependencies ===")
    
    for node in workflow.nodes:
        if isinstance(node, NodeClass):
            all_nodes[node.name] = node
            deps = extract_dependencies(node.inputs, workflow_inputs)
            node_dependencies[node.name] = deps
            
            if debug:
                print(f"Node {node.name}: dependencies = {deps}")
            
            # Add node to graph
            graph.add_node(node.name, make_task(node, fn_map, graphStateType))
                
        elif isinstance(node, CycleClass):
            # Handle cycle as a composite node
            init_name = f"{node.name}_init"
            exit_name = f"{node.name}_exit"
            
            # Add cycle init node
            inputs_dict = {inp.name: inp.default_value for inp in node.inputs if inp.default_value is not None}
            graph.add_node(init_name, make_setter(inputs_dict))
            
            # Extract dependencies for the cycle
            deps = extract_dependencies(node.inputs, workflow_inputs)
            node_dependencies[init_name] = deps
            all_nodes[init_name] = node
            
            if debug:
                print(f"Cycle {node.name} (init): dependencies = {deps}")

            # Add internal cycle nodes
            first_internal = None
            prev = None
            for cycle_node in node.nodes:
                graph.add_node(cycle_node.name, make_task(cycle_node.call, fn_map, cycle_node.when))
                if prev:
                    graph.add_edge(prev, cycle_node.name)
                prev = cycle_node.name
                if first_internal is None:
                    first_internal = cycle_node.name
            
            # Add cycle exit node and router
            graph.add_node(exit_name, lambda s: s)
            router = make_cycle_router(node.name, node.guard, first_internal, node.max_iterations)
            graph.add_conditional_edges(prev, router)
            graph.add_edge(init_name, first_internal)
            
            # Track the cycle as a unit (using init node as representative)
            all_nodes[node.name] = node
            # Don't add cycle name to node_dependencies - only init_name should be there
    
    if debug:
        print("=== Creating dependency edges ===")
    
    
    # Create dependency-based edges
    for node_name, deps in node_dependencies.items():
        for dep in deps:
            all_dependencies.add(dep)
            if dep in all_nodes and isinstance(all_nodes[dep], CycleClass):
                # Connect to cycle's exit node
                if debug:
                    print(f"Adding edge: {dep}_exit -> {node_name}")
                graph.add_(f"{dep}_exit", node_name)
            elif dep in all_nodes:
                # Regular node dependency
                if debug:
                    print(f"Adding edge: {dep} -> {node_name}")
                graph.add_edge(dep, node_name)
            else:
                raise ValueError(f"Node {dep} not found")

    output_nodes = set(node_dependencies.keys()) - all_dependencies
    if len(output_nodes) > 1:
        raise ValueError(f"There is more than one output node detected: {output_nodes}")
    if len(output_nodes) == 0:
        raise ValueError(f"There is no output node detected in {workflow.name}")
    output_node = output_nodes.pop()

    graph.add_edge(output_node, END)
    
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

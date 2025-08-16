# Runner for AWsl workflows

from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Set, Type
import argparse
from typing_extensions import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, RunnableConfig
from langgraph.channels import LastValue, BinaryOperatorAggregate
from langgraph.pregel import Pregel
from awsl.grammar.workflow_parser import (
    parse_awsl_to_objects, 
    print_workflow_structure, 
    NodeClass, 
    CycleClass, 
    Workflow,
    Reducer
)
from langgraph.pregel._read import PregelNode
from langgraph.pregel._write import ChannelWrite, ChannelWriteTupleEntry
import operator

START_NODE_NAME = "START_NODE"
NOOP_NODE_NAME = "NOOP_NODE"

class ClearValue:
    """Sentinel value to indicate a field should be explicitly cleared/set to None"""
    pass

CLEAR = ClearValue()

def reducer(a: Any | None, b: Any | None) -> Any | None:
    if isinstance(b, ClearValue):
        return None
    return b if b is not None else a

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

def make_task(node: NodeClass, fn_map: Dict[str, Any], graphStateType: Type, run_once_only: bool = False):
    func = fn_map.get(node.call)
    if not callable(func):
        raise ValueError(f"Function '{node.call}' not provided")
    already_run = [False]
    def task(state: graphStateType, config: RunnableConfig) -> graphStateType:
        all_inputs_available = all(state.get(inp.default_value) is not None 
                                   for inp in node.inputs if not inp.optional and inp.default_value is not None)
        if not all_inputs_available:
            return Command(goto=NOOP_NODE_NAME)
    
        if node.when and not _eval_condition(node.when, state):
            return Command(goto=NOOP_NODE_NAME)
        
        if run_once_only and already_run[0]:
            return Command(goto=NOOP_NODE_NAME)
        already_run[0] = True
        metadata = config.get("metadata", {})
        metadata.update({constant.name: constant.value for constant in node.constants})
        try:
            update = func(state, config = dict(config, **{"metadata": metadata})) or {}
        except Exception as e:
            print(f"Error in {node.call}: {e}")
            raise e
        update_with_node_name = {node.name + "." + k: v for k, v in update.items()}
        return update_with_node_name

    return task

def make_cycle_start_node(cycle: CycleClass, graphStateType: Type):
    iteration_key = f"{cycle.name}.iteration_counter"
    inputs_dict = {inp.name: inp.default_value for inp in cycle.inputs if inp.default_value is not None}
    def cycle_start(state: graphStateType) -> graphStateType:
        all_inputs_available = all(state.get(inp.default_value) is not None 
                                   for inp in cycle.inputs if inp.default_value is not None)
        if not all_inputs_available:
            return Command(goto=NOOP_NODE_NAME)
        count = state.get(iteration_key, 0) + 1
        update = graphStateType()
        update[iteration_key] = count
        for k, expr in inputs_dict.items():
            val = _eval_value(expr, state)
            update[cycle.name + "." + k] = val
        for out in cycle.outputs:
            val = _eval_value(out.default_value, state)
            if val is not None:
                update[cycle.name + "." + out.name] = val
        # Clear all child nodes outputs before next iteration
        for node_output in cycle.nodes_outputs:
            update[node_output] = CLEAR
            state[node_output] = None
        return update
    return cycle_start

def make_cycle_guard_node(cycle: CycleClass, graphStateType: Type):
    def cycle_guard(state: graphStateType) -> graphStateType:
        # need to take into account iteration counter because outputs will be there even after first iteration
        all_inputs_available = all(state.get(inp.default_value) is not None 
                                   for inp in cycle.outputs if inp.default_value is not None)
        if not all_inputs_available:
            return Command(goto=NOOP_NODE_NAME)
        update = {}
        for out in cycle.outputs:
            val = _eval_value(out.default_value, state)
            update[cycle.name + "." + out.name] = val
        return update

    return cycle_guard

def make_cycle_guard_router(cycle: CycleClass, cycle_start_name: str, graphStateType: Type):
    iteration_key = f"{cycle.name}.iteration_counter"

    def cycle_guard_router(state: graphStateType) -> graphStateType:
        all_inputs_available = all(state.get(cycle.name + "." + inp.name) is not None 
                                   for inp in cycle.outputs)
        if not all_inputs_available:
            return Command(goto=NOOP_NODE_NAME)
        
        count = state.get(iteration_key, 0)
        if _eval_condition(cycle.guard, state) or count >= cycle.max_iterations:
            return Command(goto=cycle.name)
        
        return Command(goto=cycle_start_name)

    return cycle_guard_router

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
                # It's a constant or a workflow input
                pass
    return dependencies

def extract_in_cycle_dependencies(inputs: List, cycle_inputs: Set[str], cycle_start_name: str) -> Set[str]:
    """Extract node dependencies from input assignments"""
    dependencies = set()
    for inp in inputs:
        if inp.default_value is not None:
            default_val = str(inp.default_value).strip()
            if default_val in cycle_inputs:
                dependencies.add(cycle_start_name)
            elif "." in default_val and not default_val.startswith('"'):
                node_name = default_val.split(".")[0]
                dependencies.add(node_name)
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
            iteration_key = f"{node.name}.iteration_counter"
            field_names.add(iteration_key)
            for out in node.outputs:
                field_names.add(node.name + "." + out.name)
            for inp in node.inputs:
                field_names.add(node.name + "." + inp.name)
            for cycle_node in node.nodes:
                for out in cycle_node.outputs:
                    field_names.add(cycle_node.name + "." + out.name)
    
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
    
    # Collect nodes dependencies
    node_dependencies = {}
    all_dependencies = set()
    number_of_cycles = 0
     # Add dummy start node
    graph.add_node(START_NODE_NAME, _Noop)
    graph.add_edge(START, START_NODE_NAME)
    graph.add_node(NOOP_NODE_NAME, _Noop)

    if debug:
        print("=== DEBUG: Node Dependencies ===")
    
    for node in workflow.nodes:
        if isinstance(node, NodeClass):
            deps = extract_dependencies(node.inputs, workflow_inputs)
            node_dependencies[node.name] = deps
            
            if debug:
                print(f"Node {node.name}: dependencies = {deps}")
            
            # Add node to graph
            graph.add_node(node.name, make_task(node, fn_map, graphStateType, run_once_only=True))
                
        elif isinstance(node, CycleClass):
            number_of_cycles += 1
            # Handle cycle as a composite node with 3 special nodes: start, 
            # guard and exit (which is the same as the cycle node)
            cycle_start_name = f"{node.name}_cycle_start"
            cycle_guard_name = f"{node.name}_cycle_guard"
            cycle_guard_router_name = f"{node.name}_cycle_guard_router"
            
            # Add cycle start node
            graph.add_node(cycle_start_name, make_cycle_start_node(node, graphStateType))
            
            # Extract dependencies for the cycle
            deps = extract_dependencies(node.inputs, workflow_inputs)
            node_dependencies[cycle_start_name] = deps
            
            if debug:
                print(f"Cycle {node.name} (init): dependencies = {deps}")
            
            cycle_inputs_and_outputs = [node.name + "." + inp.name for inp in node.inputs] + \
                                       [node.name + "." + out.name for out in node.outputs]
            nodes_outputs = []
            for cycle_node in node.nodes:
                deps = extract_in_cycle_dependencies(cycle_node.inputs, cycle_inputs_and_outputs, cycle_start_name)
                node_dependencies[cycle_node.name] = deps
                graph.add_node(cycle_node.name, make_task(cycle_node, fn_map, graphStateType))
                nodes_outputs.extend([cycle_node.name + "." + out.name for out in cycle_node.outputs])

            node.nodes_outputs = nodes_outputs
            # Add cycle exit node and router
            graph.add_node(cycle_guard_name, make_cycle_guard_node(node, graphStateType), defer=True)
            guard_deps = extract_dependencies(node.outputs, set())
            node_dependencies[cycle_guard_name] = guard_deps
            graph.add_node(node.name, _Noop)
            graph.add_node(cycle_guard_router_name, 
                           make_cycle_guard_router(node, cycle_start_name, graphStateType), 
                           defer=True)
            node_dependencies[cycle_guard_router_name] = set([cycle_guard_name])
            all_dependencies.add(cycle_guard_router_name) # To exclude guard nodes from output nodes
    if debug:
        print("=== Creating dependency edges ===")
    
    # Create dependency-based edges
    for node_name, deps in node_dependencies.items():
        for dep in deps:
            all_dependencies.add(dep)
            print(f"Adding edge: {dep} -> {node_name}")
            graph.add_edge(dep, node_name)

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

def make_cycle_guard_pregel_node(cycle: CycleClass, iteration_key: str, all_in_cycle_outputs: set[str]):
    def cycle_guard(task_input: dict) -> dict:
        all_inputs_available = all(task_input.get(inp.default_value) is not None 
                                   for inp in cycle.guard.inputs if inp.default_value is not None and not inp.optional)
        if not all_inputs_available:
            return None
        
        update = {}
        count = task_input.get(iteration_key, 0)
        if _eval_condition(cycle.guard.when, task_input) or count >= cycle.max_iterations - 1:
            # Prepare the output of the cycle block
            for out in cycle.outputs:
                val = _eval_value(out.default_value, task_input)
                update[cycle.name + "." + out.name] = val
            # And finish the cycle
            return update
        
        # This will trigger the next iteration
        update[iteration_key] = 1
        return update

    triggers = [inp.default_value for inp in cycle.guard.inputs if inp.target_node_name is not None]
    return create_pregel_node_from_params(fn=cycle_guard, 
                                          channels=triggers+[iteration_key]+list(all_in_cycle_outputs), 
                                          triggers=triggers)

def create_cycle_start_pregel_node(cycle: CycleClass, 
                                   iteration_key: str, 
                                   cycle_nodes_outputs_to_clean: list[str], 
                                   all_in_cycle_outputs: set[str]):
    inputs_dict = {inp.name: inp.default_value for inp in cycle.inputs if inp.default_value is not None}
    def cycle_start(task_input: dict) -> dict:
        update = {}
        for k, expr in inputs_dict.items():
            val = _eval_value(expr, task_input)
            update[cycle.name + "." + k] = val

        for clear_node in cycle_nodes_outputs_to_clean:
            update[clear_node] = None

        return update
    
    triggers = [inp.default_value for inp in cycle.inputs 
                if inp.default_value is not None and inp.default_value not in all_in_cycle_outputs]
    triggers.append(iteration_key)
    return create_pregel_node_from_params(fn=cycle_start, 
                                          channels=triggers + list(all_in_cycle_outputs), 
                                          triggers=triggers)

def make_pregel_task(node: NodeClass, fn_map: Dict[str, Any]):
    func = fn_map.get(node.call)
    if not callable(func):
        raise ValueError(f"Function '{node.call}' not provided")
    metadata = {constant.name: constant.value for constant in node.constants}
    def task(task_input: dict) -> dict:
        all_inputs_available = all(task_input.get(inp.default_value) is not None 
                                   for inp in node.inputs if not inp.optional and inp.default_value is not None)
        if not all_inputs_available:
            return None
    
        if node.when and not _eval_condition(node.when, task_input):
            return None
        
        inputs = {inp.name: task_input.get(inp.default_value, None) for inp in node.inputs}
        try:
            update = func(**inputs, config = metadata) or {}
        except Exception as e:
            print(f"Error in {node.call}: {e}")
            raise e
        update_with_node_name = {node.name + "." + k: v for k, v in update.items()}
        return update_with_node_name

    return task

def create_pregel_node_from_params(fn: callable, channels: List[str], triggers: List[str]):
    def update_mapper(x):
        if x is None:
            return None
        updates: list[tuple[str, Any]] = []
        for k, v in x.items():
            updates.append((k, v))
        return updates
    
    return PregelNode(
            channels=channels,
            triggers=triggers,
            tags=[],
            metadata={},
            writers=[ChannelWrite([ChannelWriteTupleEntry(mapper=update_mapper)])],
            bound=fn,
            retry_policy=[],
            cache_policy=None,
        )

def create_pregel_node(node: NodeClass, fn_map: Dict[str, Any]):
    channels = [inp.default_value for inp in node.inputs if inp.default_value is not None]
    return create_pregel_node_from_params(make_pregel_task(node, fn_map), channels, channels)

def build_pregel_graph(path: str, functions: Dict[str, Any], checkpointer: Any | None = None, debug: bool = False):
    workflow: Workflow = parse_awsl_to_objects(path)
    
    # Dynamically build fields from workflow inputs, outputs, and all node inputs/outputs
    field_names = {}
    
    # Add workflow inputs and outputs
    for inp in workflow.inputs:
        field_names[inp.name] = LastValue(Any)
    for out in workflow.outputs:
        field_names[out.name] = LastValue(Any)
    
    fn_map = dict(functions)
    
    # Get workflow input names
    workflow_inputs = {inp.name for inp in workflow.inputs}
    
    # Collect nodes dependencies
    node_dependencies = {}
    all_dependencies = set()
    number_of_cycles = 0
    nodes = {}
    cycle_iteration_keys = []
    for node in workflow.nodes:
        if isinstance(node, NodeClass):
            for out in node.outputs:
                field_names[node.name + "." + out.name] = LastValue(Any)
            deps = extract_dependencies(node.inputs, workflow_inputs)
            node_dependencies[node.name] = deps
            
            # Add node to graph
            nodes[node.name] = create_pregel_node(node, fn_map)
                
        elif isinstance(node, CycleClass):
            number_of_cycles += 1
            
            iteration_key = f"{node.name}.iteration_counter"
            cycle_iteration_keys.append(iteration_key)
            field_names[iteration_key] = BinaryOperatorAggregate(int, operator.add)
            in_cycle_node_output_names = set()
            cycle_nodes_outputs_to_clean = set()
            for out in node.outputs:
                field_names[node.name + "." + out.name] = LastValue(Any)
            for inp in node.inputs:
                field_names[node.name + "." + inp.name] = LastValue(Any)
            for in_cycle_node in node.nodes:
                for out in in_cycle_node.outputs:
                    in_cycle_node_output_names.add(in_cycle_node.name + "." + out.name)
                    if out.reducer == Reducer.APPEND:
                        field_names[in_cycle_node.name + "." + out.name] = BinaryOperatorAggregate(list[Any], operator.add) # noqa: E501
                        # we don't want to clear aggregated values
                    else:
                        field_names[in_cycle_node.name + "." + out.name] = LastValue(Any)
                        cycle_nodes_outputs_to_clean.add(in_cycle_node.name + "." + out.name)

            # Handle cycle as a composite node with 2 special nodes: start and guard
            cycle_start_name = f"{node.name}_cycle_start"
            cycle_guard_name = f"{node.name}_cycle_guard"
            
            # Add cycle start node
            nodes[cycle_start_name] = create_cycle_start_pregel_node(node, 
                                                                     iteration_key, 
                                                                     cycle_nodes_outputs_to_clean, 
                                                                     in_cycle_node_output_names)
            
            # Extract dependencies for the cycle
            deps = extract_dependencies(node.inputs, workflow_inputs)
            deps.add(cycle_guard_name)
            node_dependencies[cycle_start_name] = deps
            
            cycle_inputs_and_outputs = [node.name + "." + inp.name for inp in node.inputs] + \
                                       [node.name + "." + out.name for out in node.outputs]
            nodes_outputs = []
            for cycle_node in node.nodes:
                deps = extract_in_cycle_dependencies(cycle_node.inputs, cycle_inputs_and_outputs, cycle_start_name)
                node_dependencies[cycle_node.name] = deps
                nodes[cycle_node.name] = create_pregel_node(cycle_node, fn_map)
                nodes_outputs.extend([cycle_node.name + "." + out.name for out in cycle_node.outputs])

            #node.nodes_outputs = nodes_outputs

            # Add cycle guard node
            nodes[cycle_guard_name] = make_cycle_guard_pregel_node(node, iteration_key, in_cycle_node_output_names)
            node_dependencies[cycle_guard_name] = set([cycle_start_name])
    
    # Create dependency-based edges
    for node_name, deps in node_dependencies.items():
        for dep in deps:
            all_dependencies.add(dep)

    output_nodes = set(node_dependencies.keys()) - all_dependencies
    if len(output_nodes) > 1:
        raise ValueError(f"There is more than one output node detected: {output_nodes}")
    if len(output_nodes) == 0:
        raise ValueError(f"There is no output node detected in {workflow.name}")

    app = Pregel(
        nodes=nodes,
        channels=field_names,
        input_channels=workflow_inputs,
        output_channels=[out.default_value for out in workflow.outputs]+cycle_iteration_keys,
    )

    return app

def run_workflow(workflow_path: str,
                 fn_map=None,
                 params: Dict[str, Any] | None = None,
                 thread_id: str | None = None,
                 resume: str | None = None,
                 checkpointer: Any | None = None,
                 debug: bool = False):
    app = build_pregel_graph(workflow_path, functions=fn_map, checkpointer=checkpointer, debug=debug)
    config: Dict[str, Any] = {"configurable": {"thread_id": thread_id}, "recursion_limit": 100}
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


from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from lark import Lark, Transformer

def load_grammar() -> str:
    return (Path(__file__).with_name("awsl.bnf")).read_text()


@dataclass
class Input:
    """Represents an input parameter declaration"""
    type: str
    name: str
    default_value: Optional[Any] = None


@dataclass
class Output:
    """Represents an output parameter declaration"""
    type: str
    name: str
    default_value: Optional[Any] = None


@dataclass
class Metadata:
    """Represents workflow metadata"""
    entries: Dict[str, str] = field(default_factory=dict)


@dataclass
class HitlConfig:
    """Represents human-in-the-loop configuration"""
    correlation: str
    timeout: str


@dataclass
class RetryConfig:
    """Represents retry configuration"""
    attempts: int
    backoff: str
    policy: str


@dataclass
class NodeClass:
    """Represents a workflow node"""
    name: str
    call: str
    inputs: List[Input] = field(default_factory=list)
    outputs: List[Output] = field(default_factory=list)
    when: Optional[str] = None
    hitl: Optional[HitlConfig] = None
    retry: Optional[RetryConfig] = None
    constants: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CycleClass:
    """Represents a workflow cycle"""
    name: str
    inputs: List[Input] = field(default_factory=list)
    outputs: List[Output] = field(default_factory=list)
    nodes: List[NodeClass] = field(default_factory=list)
    guard: str = ""
    max_iterations: int = 10


@dataclass
class Workflow:
    """Represents the complete workflow"""
    name: str
    metadata: Optional[Metadata] = None
    inputs: List[Input] = field(default_factory=list)
    outputs: List[Output] = field(default_factory=list)
    steps: List[NodeClass | CycleClass] = field(default_factory=list)


class ASTBuilder(Transformer):
    def workflow(self, items):
        name = items[0]
        body = items[1]
        wf = Workflow(name=name)
        for it in body:
            if isinstance(it, Metadata):
                wf.metadata = it
            elif isinstance(it, list) and len(it) > 0 and isinstance(it[0], Input):
                wf.inputs = it
            elif isinstance(it, list) and len(it) > 0 and isinstance(it[0], Output):
                wf.outputs = it
            elif isinstance(it, (NodeClass, CycleClass)):
                wf.steps.append(it)
        return wf

    def workflow_body(self, items):
        return items

    def metadata_block(self, items):
        metadata = Metadata()
        for entry in items:
            if isinstance(entry, tuple) and len(entry) == 2:
                key, value = entry
                metadata.entries[key] = value
        return metadata

    def inputs_block(self, items):
        return [Input(type=param.type, name=param.name, default_value=param.default_value) 
                for param in items]

    def outputs_block(self, items):
        return [Output(type=param.type, name=param.name, default_value=param.default_value) 
                for param in items]

    def param_decl(self, items):
        if len(items) == 3:
            return Input(type=items[0], name=items[1], default_value=items[2])
        return Input(type=items[0], name=items[1])

    def param_value(self, items):
        # Extract the actual value from the parse tree
        if hasattr(items[0], 'children') and items[0].children:
            return items[0].children[0]
        return items[0]

    def metadata_entry(self, items):
        return (items[0], items[1])

    def node_block(self, items):
        name = items[0]
        body = items[1]
        node = NodeClass(name=name, call=body["call"])
        
        # Process node elements
        if "when" in body:
            node.when = body["when"]
        if "inputs" in body:
            node.inputs = body["inputs"]
        if "outputs" in body:
            node.outputs = body["outputs"]
        if "hitl" in body:
            node.hitl = body["hitl"]
        if "retry" in body:
            node.retry = body["retry"]
        if "constants" in body:
            node.constants = body["constants"]
            
        return node

    def node_body(self, items):
        info = {"call": items[0]}
        for it in items[1:]:
            if isinstance(it, dict):
                info.update(it)
            elif isinstance(it, list):
                # Handle inputs/outputs lists
                if len(it) > 0 and isinstance(it[0], Input):
                    info["inputs"] = it
                elif len(it) > 0 and isinstance(it[0], Output):
                    info["outputs"] = it
        return info

    def node_element(self, items):
        # unwrap single element rules
        return items[0]

    def call_stmt(self, items):
        return items[0]

    def when_clause(self, items):
        return {"when": items[0]}

    def hitl_block(self, items):
        # For now, return basic config - can be enhanced later
        return {"hitl": HitlConfig(correlation="default", timeout="24h")}

    def cycle_block(self, items):
        name = items[0]
        body = items[1]
        cycle = CycleClass(name=name)
        
        # Process cycle elements
        if "inputs" in body:
            cycle.inputs = body["inputs"]
        if "outputs" in body:
            cycle.outputs = body["outputs"]
        if "nodes" in body:
            cycle.nodes = body["nodes"]
        if "guard" in body:
            cycle.guard = body["guard"]
        if "max_iterations" in body:
            cycle.max_iterations = body["max_iterations"]
            
        return cycle

    def cycle_body(self, items):
        res = {"inputs": [], "outputs": [], "nodes": []}
        for it in items:
            if isinstance(it, NodeClass):
                res["nodes"].append(it)
            elif isinstance(it, list) and len(it) > 0 and isinstance(it[0], Input):
                res["inputs"] = it
            elif isinstance(it, list) and len(it) > 0 and isinstance(it[0], Output):
                res["outputs"] = it
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

    def BOOL(self, token):
        return str(token).lower() == "true"
    

def print_workflow_structure(workflow: Workflow, indent: int = 0) -> None:
    """Pretty print the workflow object hierarchy"""
    prefix = "  " * indent
    print(f"{prefix}Workflow: {workflow.name}")
    
    if workflow.metadata:
        print(f"{prefix}  Metadata:")
        for key, value in workflow.metadata.entries.items():
            print(f"{prefix}    {key}: {value}")
    
    if workflow.inputs:
        print(f"{prefix}  Inputs:")
        for inp in workflow.inputs:
            default = f" = {inp.default_value}" if inp.default_value is not None else ""
            print(f"{prefix}    {inp.type} {inp.name}{default}")
    
    if workflow.outputs:
        print(f"{prefix}  Outputs:")
        for out in workflow.outputs:
            default = f" = {out.default_value}" if out.default_value is not None else ""
            print(f"{prefix}    {out.type} {out.name}{default}")
    
    print(f"{prefix}  Steps:")
    for step in workflow.steps:
        if isinstance(step, NodeClass):
            print(f"{prefix}    NodeClass: {step.name}")
            print(f"{prefix}      call: {step.call}")
            if step.when:
                print(f"{prefix}      when: {step.when}")
            if step.inputs:
                print(f"{prefix}      inputs:")
                for inp in step.inputs:
                    default = f" = {inp.default_value}" if inp.default_value is not None else ""
                    print(f"{prefix}        {inp.type} {inp.name}{default}")
            if step.outputs:
                print(f"{prefix}      outputs:")
                for out in step.outputs:
                    default = f" = {out.default_value}" if out.default_value is not None else ""
                    print(f"{prefix}        {out.type} {out.name}{default}")
            if step.hitl:
                print(f"{prefix}      hitl: correlation={step.hitl.correlation}, timeout={step.hitl.timeout}")
        elif isinstance(step, CycleClass):
            print(f"{prefix}    CycleClass: {step.name}")
            print(f"{prefix}      guard: {step.guard}")
            print(f"{prefix}      max_iterations: {step.max_iterations}")
            if step.inputs:
                print(f"{prefix}      inputs:")
                for inp in step.inputs:
                    default = f" = {inp.default_value}" if inp.default_value is not None else ""
                    print(f"{prefix}        {inp.type} {inp.name}{default}")
            if step.outputs:
                print(f"{prefix}      outputs:")
                for out in step.outputs:
                    default = f" = {out.default_value}" if out.default_value is not None else ""
                    print(f"{prefix}        {out.type} {out.name}{default}")
            print(f"{prefix}      nodes:")
            for node in step.nodes:
                print(f"{prefix}        NodeClass: {node.name}")
                print(f"{prefix}          call: {node.call}")
                if node.when:
                    print(f"{prefix}          when: {node.when}")
                if node.inputs:
                    print(f"{prefix}          inputs:")
                    for inp in node.inputs:
                        default = f" = {inp.default_value}" if inp.default_value is not None else ""
                        print(f"{prefix}            {inp.type} {inp.name}{default}")
                if node.outputs:
                    print(f"{prefix}          outputs:")
                    for out in node.outputs:
                        default = f" = {out.default_value}" if out.default_value is not None else ""
                        print(f"{prefix}            {out.type} {out.name}{default}")
                if node.hitl:
                    print(f"{prefix}          hitl: correlation={node.hitl.correlation}, timeout={node.hitl.timeout}")


def parse_awsl_to_objects(path: str) -> Workflow:
    """Parse AWSL file and return structured object hierarchy"""
    grammar = load_grammar()
    parser = Lark(grammar, start="workflow")
    tree = parser.parse(Path(path).read_text())
    transformer = ASTBuilder()
    return transformer.transform(tree)

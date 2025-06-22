from pathlib import Path
import importlib
from bpmn_workflows import compat  # noqa: F401  # apply networkx compatibility
from bpmn_python.bpmn_diagram_rep import BpmnDiagramGraph
import argparse
import xmlschema
import xml.etree.ElementTree as ET
from bpmn_ext.generate_ext_schema import generate_ext_schema

from bpmn_ext.bpmn_ext import collect_operations, generate_xsd, validate_operations, EXT_NS


def validate_bpmn(path: str, functions_module: str) -> bool:
    diagram = BpmnDiagramGraph()
    diagram.load_diagram_from_xml_file(path)
    # simple validation: ensure nodes and flows were loaded
    nodes = diagram.get_nodes()
    flows = diagram.sequence_flows
    print(f"Loaded {len(nodes)} nodes and {len(flows)} flows")

    # generate extension schema from decorated functions
    ext_path = Path(path).parent / "bpmn_ext.xsd"
    generate_ext_schema(functions_module, ext_path)

    # validate extension elements against generated schema
    schema = xmlschema.XMLSchema(str(ext_path))
    tree = ET.parse(path)
    root_el = tree.getroot()
    ns = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL", "ext": EXT_NS}
    for op_el in root_el.findall(".//bpmn:extensionElements/ext:operation", ns):
        schema.validate(op_el)
    return len(nodes) > 0 and len(flows) > 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Validate a BPMN XML file.')
    parser.add_argument('xml_path', help='Path to the BPMN XML file to validate')
    parser.add_argument('--functions', default='steps.example_functions',
                      help='Python module containing the workflow functions (default: steps.example_functions)')
    args = parser.parse_args()

    if validate_bpmn(args.xml_path, args.functions):
        print("BPMN file is valid for bpmn_python")
    else:
        print("BPMN file failed validation")

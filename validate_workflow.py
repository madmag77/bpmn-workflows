from pathlib import Path
import importlib
from bpmn_workflows import compat  # noqa: F401  # apply networkx compatibility
from bpmn_python.bpmn_diagram_rep import BpmnDiagramGraph
import argparse
import xmlschema
import xml.etree.ElementTree as ET

from bpmn_ext import collect_operations, generate_xsd, validate_operations, EXT_NS


def validate_bpmn(path: str) -> bool:
    diagram = BpmnDiagramGraph()
    diagram.load_diagram_from_xml_file(path)
    # simple validation: ensure nodes and flows were loaded
    nodes = diagram.get_nodes()
    flows = diagram.sequence_flows
    print(f"Loaded {len(nodes)} nodes and {len(flows)} flows")

    # generate extension schema from decorated functions
    mod = importlib.import_module("workflow_functions")
    ops = collect_operations(mod)
    ext_path = Path("bpmn_ext.xsd")
    ext_path.write_text(generate_xsd(ops))

    # validate extension elements against generated schema
    schema = xmlschema.XMLSchema(str(ext_path))
    tree = ET.parse(path)
    root_el = tree.getroot()
    ns = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL", "ext": EXT_NS}
    for op_el in root_el.findall(".//bpmn:extensionElements/ext:operation", ns):
        schema.validate(op_el)
    validate_operations(path, ops)
    return len(nodes) > 0 and len(flows) > 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Validate a BPMN XML file.')
    parser.add_argument('xml_path', help='Path to the BPMN XML file to validate')
    args = parser.parse_args()

    if validate_bpmn(args.xml_path):
        print("BPMN file is valid for bpmn_python")
    else:
        print("BPMN file failed validation")

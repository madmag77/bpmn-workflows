from bpmn_workflows import compat  # noqa: F401  # apply networkx compatibility
from bpmn_python.bpmn_diagram_rep import BpmnDiagramGraph
import argparse


def validate_bpmn(path: str) -> bool:
    diagram = BpmnDiagramGraph()
    diagram.load_diagram_from_xml_file(path)
    # simple validation: ensure nodes and flows were loaded
    nodes = diagram.get_nodes()
    flows = diagram.sequence_flows
    print(f"Loaded {len(nodes)} nodes and {len(flows)} flows")
    return len(nodes) > 0 and len(flows) > 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Validate a BPMN XML file.')
    parser.add_argument('xml_path', help='Path to the BPMN XML file to validate')
    args = parser.parse_args()

    if validate_bpmn(args.xml_path):
        print("BPMN file is valid for bpmn_python")
    else:
        print("BPMN file failed validation")

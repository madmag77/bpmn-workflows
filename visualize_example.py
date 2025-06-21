from bpmn_workflows import compat  # noqa: F401
from bpmn_python.bpmn_diagram_rep import BpmnDiagramGraph
from bpmn_python.bpmn_diagram_visualizer import bpmn_diagram_to_png


def visualize(path: str, output: str):
    diagram = BpmnDiagramGraph()
    diagram.load_diagram_from_xml_file(path)
    bpmn_diagram_to_png(diagram, output)
    print(f"Image saved to {output}.png")


if __name__ == "__main__":
    import sys
    xml_path = sys.argv[1] if len(sys.argv) > 1 else "example1.xml"
    out_name = sys.argv[2] if len(sys.argv) > 2 else "example1"
    visualize(xml_path, out_name)

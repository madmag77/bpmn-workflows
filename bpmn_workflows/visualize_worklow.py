from bpmn_workflows import compat  # noqa: F401
from bpmn_python.bpmn_diagram_rep import BpmnDiagramGraph
from bpmn_python.bpmn_diagram_visualizer import bpmn_diagram_to_png
import argparse


def visualize(path: str, output: str):
    diagram = BpmnDiagramGraph()
    diagram.load_diagram_from_xml_file(path)
    bpmn_diagram_to_png(diagram, output)
    print(f"Image saved to {output}.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Visualize a BPMN XML file as PNG.')
    parser.add_argument('xml_path', help='Path to the BPMN XML file to visualize')
    parser.add_argument('--output', '-o', default='workflow',
                      help='Output filename (without extension, defaults to "workflow")')
    args = parser.parse_args()

    visualize(args.xml_path, args.output)

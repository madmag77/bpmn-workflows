from __future__ import annotations
import importlib
import argparse
from pathlib import Path
from bpmn_ext.bpmn_ext import collect_operations, generate_xsd

def generate_ext_schema(module: str, output: str):
    mod = importlib.import_module(module)
    ops = collect_operations(mod)
    xsd = generate_xsd(ops)
    output_path = Path(output)
    output_path.write_text(xsd)
    print(f"Wrote {output_path} with {len(ops)} operations")

def parse_args():
    parser = argparse.ArgumentParser(description='Generate BPMN extension schema from module operations')
    parser.add_argument('--module', default='steps.example_functions',
                      help='Python module containing the operations (default: steps.example_functions)')
    parser.add_argument('--output', default='bpmn_ext/bpmn_ext.xsd',
                      help='Output path for the XSD file (default: bpmn_ext/bpmn_ext.xsd)')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    generate_ext_schema(args.module, args.output)

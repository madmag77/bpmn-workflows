from __future__ import annotations
import importlib
from pathlib import Path
from bpmn_ext import collect_operations, generate_xsd

MODULE = 'steps.example_functions'
OUTPUT = Path('bpmn_ext/bpmn_ext.xsd')

if __name__ == '__main__':
    mod = importlib.import_module(MODULE)
    ops = collect_operations(mod)
    xsd = generate_xsd(ops)
    OUTPUT.write_text(xsd)
    print(f"Wrote {OUTPUT} with {len(ops)} operations")

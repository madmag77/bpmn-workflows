# Context
This repository was created with the puropse to play with BPMN as a meta model for workflows formal definitions.

The idea is that we can use BPMN syntax and meta semantics to build workflow descriptions in XML that will be then read by python script and used to instantiate real workflows in Langgraph and run them when needed.

# Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Validate the provided BPMN file:

```bash
python validate_workflow.py examples/example_1/example1.xml
```

Generate a PNG visualisation (the image is not tracked in the repository):

```bash
brew install graphviz
python visualize_worklow.py examples/example_1/example1.xml example1
```
The image will be saved as `example1.png` in the current directory.

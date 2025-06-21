# BPMN Workflows Runner

A Python-based tool for executing BPMN workflows using LangGraph. This tool allows you to run BPMN workflows defined in XML files, with customizable workflow functions and input parameters.

## Structure

- `run_bpmn_workflow.py` - The main script for parsing and executing BPMN workflows
- `workflow_functions.py` - Collection of workflow functions that can be used in BPMN tasks
- `validate_workflow.py` - Script to validate BPMN XML files
- `visualize_workflow.py` - Script to generate visual diagrams of workflows
- `examples/` - Directory containing example workflows
  - `example_1/` - Example workflow with QA processing logic

## Setup

1. Make sure you have Python 3.x installed
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. For visualization support, install Graphviz:
```bash
brew install graphviz  # On macOS
# or
sudo apt-get install graphviz  # On Ubuntu/Debian
```

## Usage

### Running Workflows

The script takes a path to a BPMN XML file and allows passing arbitrary input parameters:

```bash
python run_bpmn_workflow.py <path_to_bpmn_xml> --param key1=value1 --param key2=value2
```

Example:
```bash
python run_bpmn_workflow.py examples/example_1/example1.xml --param input_text=hello --param rephraseCount=0
```

### Validating Workflows

Before running a workflow, you can validate the BPMN XML file:

```bash
python validate_workflow.py examples/example_1/example1.xml
```

This will check:
- XML syntax
- BPMN schema compliance
- Presence of required elements
- Referenced function availability

### Visualizing Workflows

Generate a PNG visualization of your workflow:

```bash
python visualize_workflow.py examples/example_1/example1.xml example1
```

This will create `example1.png` in the current directory, showing:
- All workflow nodes and their types
- Flow connections
- Gateway conditions
- Task function references

### Parameters

- First argument: Path to the BPMN XML file
- `--param`: Key-value pairs for workflow input (can be used multiple times)
  - Values are automatically converted to numbers when possible
  - String values are preserved as-is

### Example Output

```python
{
    'input_text': 'hello',
    'rephraseCount': 0,
    'intent': 'qa',
    'query': 'clarified hello',
    'chunks': ['chunk for clarified hello'],
    'relevance': 'OK',
    'answer': "Answer based on ['chunk for clarified hello']"
}
```

## Workflow Functions

The `workflow_functions.py` file contains all the functions that can be referenced in BPMN service tasks. Current functions include:

- `identify_user_intent`: Analyzes input and returns intent
- `ask_user`: Clarifies the input query
- `retrieve_financial_documents`: Retrieves relevant documents
- `evaluate_relevance`: Evaluates document relevance
- `rephrase_query`: Rephrases the query
- `increment_counter`: Increments a counter
- `summarize`: Summarizes input text
- `generate_answer`: Generates final answer

## Creating New Workflows

1. Create a new directory under `examples/`
2. Add your BPMN XML file
3. Reference functions from `workflow_functions.py` in your service tasks
4. Validate your workflow using `validate_workflow.py`
5. Generate a visualization using `visualize_workflow.py`
6. Run using the script as shown above

## BPMN Support

The tool supports the following BPMN elements:
- Service Tasks
- Exclusive Gateways
- Start Events
- End Events
- Sequence Flows with conditions

Service tasks should reference functions using the Camunda expression format: `${functionName}`

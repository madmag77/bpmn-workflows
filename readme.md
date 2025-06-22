# BPMN Workflows Runner

A Python-based tool for executing BPMN workflows using LangGraph. This tool allows you to run BPMN workflows defined in XML files, with customizable workflow functions and input parameters.

## Structure

- `run_bpmn_workflow.py` - The main script for parsing and executing BPMN workflows
- `steps/example_functions.py` - Collection of workflow functions that can be used in BPMN tasks
- `validate_workflow.py` - Script to validate BPMN XML files
- `visualize_workflow.py` - Script to generate visual diagrams of workflows
- `generate_ext_schema.py` - Script to generate BPMN extension schema from decorated functions
- `bpmn_ext.py` - Module for BPMN extension support and operation decorators
- `workflows/` - Directory containing workflows
  - `example_1/` - Example workflow with QA processing logic

## Setup

1. Make sure you have Python 3.x installed
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

Install postgres for storing checkpoints
```bash
brew install postgresql@15
echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc
```

1. For visualization support, install Graphviz:
```bash
brew install graphviz  # On macOS
# or
sudo apt-get install graphviz  # On Ubuntu/Debian
```

## Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality. To set up pre-commit:

1. Install pre-commit:
```bash
pip install pre-commit
```

2. Install the pre-commit hooks:
```bash
pre-commit install
```

The following hooks are configured:
- Ruff: Python linter for fast code quality checks
  - Line length: 120 characters
  - Selected rules: E (pycodestyle errors), F (pyflakes)

To run the hooks manually:
```bash
pre-commit run --all-files
```

## Usage

### Running Workflows

The script takes a path to a BPMN XML file and allows passing arbitrary input parameters:

```bash
python run_bpmn_workflow.py <path_to_bpmn_xml> --param key1=value1 --param key2=value2
```

Example:
```bash
python run_bpmn_workflow.py workflows/example_1/example1.xml --param input_text=hello --param rephraseCount=0
```

### Testing Workflows

The project includes a test suite to verify workflow behavior. Tests are located in the `tests` directory and can be run using pytest:

```bash
pytest -q
```

Example test files demonstrate how to test different workflow branches and scenarios:
- `test_branch_qa_ok.py` - Testing successful QA flow
- `test_branch_qa_rephrase.py` - Testing query rephrasing
- `test_branch_qa_error.py` - Testing error handling
- `test_branch_summarize.py` - Testing summarization flow
- `test_branch_not_clear.py` - Testing unclear input handling

To create new tests:
1. Create a new test file in the `tests` directory
2. Import necessary helper functions from `helper.py`
3. Define test functions that verify specific workflow paths
4. Run tests using pytest to ensure workflow behaves as expected

### Validating Workflows

Before running a workflow, you can validate the BPMN XML file:

```bash
python validate_workflow.py workflows/example_1/example1.xml --functions steps.example_functions
```

This will check:
- XML syntax
- BPMN schema compliance
- Presence of required elements
- Referenced function availability
- Extension elements against generated schema (generated near the XML file)
- Operation input/output parameters

The `--functions` parameter specifies the Python module containing your workflow functions. This allows you to have different sets of workflow functions for different BPMN files, each with their own schema extensions.

### Generating Extension Schema

The extension schema is automatically generated during validation. The schema file (`bpmn_ext.xsd`) is created in the same directory as your BPMN XML file. This means:

- Each BPMN workflow can have its own extension schema
- The schema is generated from the specified functions module
- Multiple workflows can use different function sets
- Schema location makes it easier to package and distribute workflows

For example:
```bash
python validate_workflow.py workflows/workflow1/process.xml --functions steps.functions1
# Generates workflows/workflow1/bpmn_ext.xsd

python validate_workflow.py workflows/workflow2/process.xml --functions steps.functions2
# Generates workflows/workflow2/bpmn_ext.xsd
```

Each generated schema will contain only the operations defined in its respective functions module.

### Visualizing Workflows

Generate a PNG visualization of your workflow:

```bash
python visualize_workflow.py workflows/example_1/example1.xml example1
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

The `steps/example_functions.py` file contains all the functions that can be referenced in BPMN service tasks. Functions are decorated with `@bpmn_op` to declare:

- Operation name
- Input parameters and their types
- Output parameters and their types

Example:
```python
@bpmn_op(
    name="identify_user_intent",
    inputs={"input_text": str},
    outputs={"intent": str}
)
def identify_user_intent(state):
    # Function implementation
    return {"intent": "qa"}
```

Current functions include:

- `identify_user_intent`: Analyzes input and returns intent
- `ask_user`: Clarifies the input query
- `retrieve_financial_documents`: Retrieves relevant documents
- `evaluate_relevance`: Evaluates document relevance
- `rephrase_query`: Rephrases the query
- `increment_counter`: Increments a counter
- `summarize`: Summarizes input text
- `generate_answer`: Generates final answer

## Creating New Workflows

1. Create a new directory under `workflows/`
2. Add your BPMN XML file
3. Create workflow functions with `@bpmn_op` decorators
4. Reference functions in service tasks with extension elements:
```xml
<serviceTask id="MyTask" camunda:expression="${my_function}">
  <extensionElements>
    <ext:operation name="my_function">
      <ext:in name="input1"/>
      <ext:out name="output1"/>
    </ext:operation>
  </extensionElements>
</serviceTask>
```
5. Generate schema: `python generate_ext_schema.py`
6. Validate workflow: `python validate_workflow.py`
7. Generate visualization: `python visualize_workflow.py`
8. Run using the script as shown above

## BPMN Support

The tool supports the following BPMN elements:
- Service Tasks with extension elements
- Exclusive Gateways
- Start Events
- End Events
- Sequence Flows with conditions

Service tasks should:
1. Reference functions using the Camunda expression format: `${functionName}`
2. Declare operation parameters using extension elements
3. Match the function's declared inputs and outputs

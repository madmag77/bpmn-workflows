# BPMN Workflows Runner

A Python-based tool for executing BPMN workflows using LangGraph. This tool allows you to run BPMN workflows defined in XML files, with customizable workflow functions and input parameters.

## Structure

- `bpmn_workflows/run_bpmn_workflow.py` - The main script for parsing and executing BPMN workflows
- `steps/example_functions.py` - Collection of workflow functions that can be used in BPMN tasks
- `steps/deepresearch_functions.py` - Functions for deep research workflow
- `bpmn_workflows/validate_workflow.py` - Script to validate BPMN XML files
- `bpmn_workflows/visualize_worklow.py` - Script to generate visual diagrams of workflows
- `bpmn_ext/generate_ext_schema.py` - Script to generate BPMN extension schema from decorated functions
- `bpmn_ext/bpmn_ext.py` - Module for BPMN extension support and operation decorators
- `chainlit_ui/` - Chainlit web interface for the deep research workflow
- `backend/` - FastAPI service exposing REST API endpoints for workflow management
- `frontend/` - React interface built with Vite to interact with the backend
- `worker/` - Background worker implementation that processes workflows from database queue
- `workflows/` - Directory containing workflows
  - `example_1/` - Example workflow with QA processing logic
  - `deepresearch/` - Deep research workflow

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
python bpmn_workflows/run_bpmn_workflow.py <path_to_bpmn_xml> --param key1=value1 --param key2=value2
```

Example:

```bash
python bpmn_workflows/run_bpmn_workflow.py workflows/example_1/example1.xml --param input_text=hello --param rephraseCount=0
```

### Testing Workflows

The project includes comprehensive test suites for both Python and Node.js components:

**Python Tests:**
Tests are located in the `tests` directory and can be run using pytest:

```bash
pytest -q
```

**Node.js Tests:**
Frontend tests are located in the `frontend/` directory and can be run using Jest. Make sure to install dependencies first:

```bash
cd frontend
npm install
npm test
```

### Validating Workflows

Before running a workflow, you can validate the BPMN XML file:

```bash
python bpmn_workflows/validate_workflow.py workflows/example_1/example1.xml --functions steps.example_functions
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
python bpmn_workflows/validate_workflow.py workflows/workflow1/process.xml --functions steps.functions1
# Generates workflows/workflow1/bpmn_ext.xsd

python bpmn_workflows/validate_workflow.py workflows/workflow2/process.xml --functions steps.functions2
# Generates workflows/workflow2/bpmn_ext.xsd
```

Each generated schema will contain only the operations defined in its respective functions module.

### Visualizing Workflows

Generate a PNG visualization of your workflow:

```bash
python bpmn_workflows/visualize_workflow.py workflows/example_1/example1.xml example1
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

## Backend API

The FastAPI backend provides the following REST endpoints:

### Workflow Templates

- `GET /workflow-templates` - List available workflow templates
- Returns: List of templates with id, name, and path

### Workflow Management

- `POST /workflows` - Start a new workflow
  - Body: `{"template_name": "string", "query": "string"}`
  - Returns: `{"id": "string", "status": "queued", "result": {}}`

- `GET /workflows` - List all workflow runs (history)
  - Returns: List of workflow runs with id, template, status, and created_at

- `GET /workflows/{workflow_run_id}` - Get workflow details
  - Returns: Workflow details including id, template, status, and result

- `POST /workflows/{workflow_run_id}/continue` - Continue a workflow waiting for input
  - Body: `{"query": "string"}`
  - Returns: Updated workflow status

### Workflow Statuses

- `queued` - Workflow is queued for execution
- `running` - Workflow is currently being processed
- `needs_input` - Workflow is waiting for user input (human-in-the-loop)
- `succeeded` - Workflow completed successfully
- `failed` - Workflow failed with an error

## Worker System

The worker system consists of a background worker pool that:

- Polls the database for queued workflows
- Executes workflows using the LangGraph framework
- Handles workflow checkpointing and state management
- Supports concurrent workflow execution
- Manages human-in-the-loop interactions

### Running Backend and Workers

You can run both the backend API server and worker pool together:

```bash
python backend_run.py
```

This will start:

- FastAPI server on port 8000
- Worker pool with configurable concurrency (default: 4 workers)
- Both services run concurrently and share the same database

### Environment Variables

- `DATABASE_URL` - PostgreSQL connection string
- `WORKERS` - Number of concurrent workers (default: 4)

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

5. Generate schema: `python bpmn_ext/generate_ext_schema.py`
6. Validate workflow: `python bpmn_workflows/validate_workflow.py`
7. Generate visualization: `python bpmn_workflows/visualize_workflow.py`
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

## Running Chainlit UI

The project includes a Chainlit-based web interface for the deep research workflow. You can run it in two ways:

### Using VSCode

1. Open the project in VSCode
2. Press F5 or go to Run and Debug
3. Select "Chainlit" from the dropdown menu
4. Click the play button or press F5

### Using Terminal

```bash
cd chainlit_ui
chainlit run main.py
```

The UI will be available at <http://localhost:8000/chainlit>

Note: Make sure you have all dependencies installed and PostgreSQL running for checkpointing support.

## Backend API

The `backend` folder contains a FastAPI application that exposes endpoints for
listing available workflow templates and starting or continuing workflows.

### Running the backend

```bash
cd backend
uvicorn main:app --reload
```

The API will be available at <http://localhost:8000/> by default.

## Frontend

The `frontend` folder hosts a small React application created with Vite. It
communicates with the backend API to list workflow history, launch new runs and
continue those waiting for user input.

### Running the frontend

```bash
cd frontend
npm install
npm run dev
```

This starts a development server, usually reachable at
<http://localhost:5173>.

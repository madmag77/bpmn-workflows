# BPMN Workflows Project

This repository contains BPMN workflow definitions and their implementations for various agent-based tasks.

## Project Structure

```
bpmn-workflows/
├── AGENTS.md
├── readme.md
├── requirements.txt
├── pyproject.toml
├── LICENSE
├── backend/                        # FastAPI service exposing REST API endpoints for workflow management
├── backend_run.py                  # Script to run both backend and worker pool concurrently
├── bpmn_ext/                       # BPMN extension utilities
├── bpmn_workflows/                 # helper functions for interacting with bpmn syntax
│   ├── __init__.py
│   ├── compat.py
│   ├── run_bpmn_workflow.py       # entry point to run workflows
│   ├── validate_workflow.py        # should be used to validate workflow in xml format after each change of it
│   └── visualize_worklow.py
├── bpmn_workflows.egg-info/        # package metadata
├── chainlit_ui/                    # Chainlit UI implementation
├── components/                     # reusable workflow components
│   └── web_scraper.py
├── frontend/                       # React interface built with Vite
├── prompts/                        # prompts for functions in steps
├── scripts/                        # utility scripts
├── steps/                          # implementations of the workflow steps for different workflows
│   ├── deepresearch_functions.py   # implementation of the workflow steps for deepresearch workflow
│   └── example_functions.py
├── tests/                          # test files (Python tests using pytest)
├── worker/                         # Background worker implementation
│   ├── db.py                      # Database interaction for workflow execution
│   └── worker_pool.py             # Worker pool that processes workflows from database queue
└── workflows/                      # BPMN workflow definitions
    ├── deepresearch/
    └── example_1/
```

The `backend` and `frontend` folders contain a FastAPI service and a Vite-based
React application. The `worker` folder contains a background worker pool that
processes workflows from the database queue. They can be started separately or
together using `backend_run.py` to provide an API, web interface, and workflow
execution system.

## Development Setup

We use:

1. BPMN xml based syntax for workflows definitions
2. [LangGraph](https://langchain-ai.github.io/langgraph/concepts/why-langgraph/) for the workflow implementation
3. Postgres as a checkpoints storage
4. [LlamaIndex](https://docs.llamaindex.ai/en/stable/) for any interactions with LLM

The project uses:

- `ruff` for linting and code formatting
- `pytest` for testing
- `pre-commit` hooks for code quality

### Running Tests

**Python Tests:**

```bash
pytest -q
```

**Node.js Tests:**

```bash
cd frontend
npm test
```

### Running Backend and Workers

You can run both the backend API server and worker pool together:

```bash
python backend_run.py
```

This will start:

- FastAPI server on port 8000 (accessible at <http://localhost:8000/api/docs>)
- Worker pool with configurable concurrency (default: 4 workers)
- Both services run concurrently and share the same database

### Environment Variables

- `DATABASE_URL` - PostgreSQL connection string
- `WORKERS` - Number of concurrent workers (default: 4)

## Backend API

The FastAPI backend provides REST endpoints for workflow management:

### Workflow Templates

- `GET /workflow-templates` - List available workflow templates

### Workflow Management

- `POST /workflows` - Start a new workflow
- `GET /workflows` - List all workflow runs (history)
- `GET /workflows/{workflow_run_id}` - Get workflow details
- `POST /workflows/{workflow_run_id}/continue` - Continue a workflow waiting for input

### Workflow Statuses

- `queued` - Workflow is queued for execution
- `running` - Workflow is currently being processed
- `needs_input` - Workflow is waiting for user input (human-in-the-loop)
- `succeeded` - Workflow completed successfully
- `failed` - Workflow failed with an error

## Worker System

The worker system consists of a background worker pool that:

- Polls the database for queued workflows
- Executes workflows using the LangGraph framework, which handles workflow checkpointing and state management
- Supports concurrent workflow execution
- Manages human-in-the-loop interactions

## The main work is happening on DeepResearch Workflow

The DeepResearch workflow is defined in `workflows/deepresearch/deepresearch.xml` file in BPNM syntax.

### Workflow Overview

1. **analyse_user_query**
   - Input: `query`
   - Output: `extended_query`, `questions`
   - Purpose: Analyzes the initial user query to determine if clarification is needed

2. **ask_questions**
   - Input: `questions`
   - Output: `clarifications`
   - Purpose: Interacts with the user to get clarifying information using Human in the loop technique

3. **query_extender**
   - Input: `query`, `clarifications`, `next_query`
   - Output: `extended_query`
   - Purpose: Extends the query based on clarifications and previous iterations

4. **retrieve_from_web**
   - Input: `extended_query`
   - Output: `chunks`
   - Purpose: Retrieves relevant information from web sources

5. **process_info**
   - Input: `query`, `chunks`, `answer_draft`
   - Output: `answer_draft`
   - Purpose: Processes retrieved information into a coherent answer

6. **answer_validate**
   - Input: `answer_draft`
   - Output: `is_enough`, `next_query`
   - Purpose: Validates if the answer is complete or needs more information

7. **final_answer_generation**
   - Input: `query`, `answer_draft`
   - Output: `final_answer`
   - Purpose: Generates the final, polished answer

### Tests

Don't forget to create and run tests for any new feature created.

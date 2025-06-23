# BPMN Workflows Project

This repository contains BPMN workflow definitions and their implementations for various agent-based tasks.

## Project Structure

```
bpmn-workflows/
├── README.md
├── AGENTS.md
├── requirements.txt
├── .pre-commit-config.yaml
├── workflows/
│   └── deepresearch/
│       ├── deepresearch.xml        # BPMN workflow definition
│       ├── agents.py               # Agent implementations
│       └── tests/
│           └── test_deepresearch.py
└── tests/
|    └── test_branch_not_clear.py      
├── steps/                          # implementations of the workflow steps for different workflows
│   └── deepresearch_functions.py   # implementation of the workflow steps for deepresearch workflow
├── prompts/                        # prompts for functions in steps
├── bpmn_workflows/                 # helper functions for interacting with bpmn syntax
├── run_bpmn_workflows.py           # entry point to run workflows
├── validate_workflow.py            # should be used to validate workflow in xml format after each change of it
```

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

```bash
pytest -q
```

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
Tests for deepresearch are located at `tests/test_deepresearch_questions.py` (common tests) and `tests/test_deepresearch.py` (human in the loop tests) files.
Don't forget to create and run tests for any new feature created. 

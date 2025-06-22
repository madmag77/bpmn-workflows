import uuid
import shutil
import psycopg
import testing.postgresql
from langgraph.checkpoint.postgres import PostgresSaver
from .helper import run_workflow
import pytest

if not shutil.which("initdb"):
    pytest.skip("PostgreSQL binaries not available", allow_module_level=True)

XML_PATH = "workflows/example_1/example1.xml"

def create_saver():
    # Create a temporary PostgreSQL instance
    postgresql = testing.postgresql.Postgresql()
    uri = postgresql.url()
    saver_cm = PostgresSaver.from_conn_string(uri)
    saver = saver_cm.__enter__()
    saver.setup()
    return saver, postgresql, saver_cm

def drop_saver(saver, postgresql, saver_cm):
    saver_cm.__exit__(None, None, None)
    postgresql.stop()

def test_postgres_resume_success():
    saver, postgresql, cm = create_saver()
    try:
        # first run interrupted before any task executes
        result = run_workflow(
            XML_PATH,
            checkpointer=saver,
            thread_id="flow1",
            interrupt_after="*",
        )
        assert result["input_text"] == "hello"
        assert "answer" not in result

        # second run continues from saved state
        result2 = run_workflow(
            XML_PATH,
            checkpointer=saver,
            thread_id="flow1",
        )
        assert result2["intent"] == "qa"
        assert "answer" in result2
    finally:
        drop_saver(saver, postgresql, cm)

def test_postgres_resume_error():
    saver, postgresql, cm = create_saver()
    try:
        def always_bad(state):
            return {"relevance": "BAD"}

        result = run_workflow(
            XML_PATH,
            fn_overrides={"evaluate_relevance": always_bad},
            params={"rephraseCount": 3},
            checkpointer=saver,
            thread_id="flow2",
            interrupt_after="*",
        )
        assert result["input_text"] == "hello"
        assert "answer" not in result

        result2 = run_workflow(
            XML_PATH,
            fn_overrides={"evaluate_relevance": always_bad},
            params={"rephraseCount": 3},
            checkpointer=saver,
            thread_id="flow2",
        )
        assert result2.get("relevance") == "BAD"
        assert "answer" in result2
    finally:
        drop_saver(saver, postgresql, cm)

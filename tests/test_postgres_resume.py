import uuid
import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from .helper import run_workflow

XML_PATH = "examples/example_1/example1.xml"
DB_ROOT_URI = "postgresql://postgres:postgres@localhost/postgres"

def create_saver():
    dbname = "test_" + uuid.uuid4().hex[:8]
    with psycopg.connect(DB_ROOT_URI, autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {dbname}")
    uri = f"postgresql://postgres:postgres@localhost/{dbname}"
    saver_cm = PostgresSaver.from_conn_string(uri)
    saver = saver_cm.__enter__()
    saver.setup()
    return saver, dbname, saver_cm

def drop_saver(saver, dbname, saver_cm):
    saver_cm.__exit__(None, None, None)
    with psycopg.connect(DB_ROOT_URI, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {dbname}")

def test_postgres_resume_success():
    saver, dbname, cm = create_saver()
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
        drop_saver(saver, dbname, cm)

def test_postgres_resume_error():
    saver, dbname, cm = create_saver()
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
        drop_saver(saver, dbname, cm)

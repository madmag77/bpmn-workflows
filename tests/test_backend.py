import os
import tempfile
from fastapi.testclient import TestClient

# use temporary sqlite db for tests
fd, path = tempfile.mkstemp()
os.close(fd)
os.environ["DATABASE_URL"] = f"sqlite:///{path}"

from backend import main  # noqa: E402


def dummy_run(*args, **kwargs):
    return {"final_answer": "answer"}


def test_templates():
    with TestClient(main.app) as client:
        resp = client.get("/workflow-templates")
        assert resp.status_code == 200
        assert any(t["id"] == "deepresearch" for t in resp.json())


def test_start_and_continue(monkeypatch):
    with TestClient(main.app) as client:
        start = client.post("/workflows", json={"template_name": "deepresearch", "query": "hi"})
        assert start.status_code == 200
        wf_id = start.json()["id"]
        assert start.json()["status"] == "queued"
        cont = client.post(f"/workflows/{wf_id}/continue", json={"query": "ok"})
        assert cont.status_code == 400  # cannot continue yet

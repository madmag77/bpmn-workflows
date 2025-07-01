from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

import steps.deepresearch_functions as drf
from bpmn_workflows.run_bpmn_workflow import run_workflow
from langgraph.checkpoint.postgres import PostgresSaver

from backend.database import init_db, get_session
from backend.models import WorkflowRun
from backend.workflow_loader import list_templates, get_template

POSTGRES_URL = os.getenv("DATABASE_URL")

FN_MAP = {name: getattr(drf, name) for name in dir(drf) if not name.startswith("_")}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown
    pass

app = FastAPI(lifespan=lifespan, docs_url="/api/docs")


@app.get("/workflow-templates")
def templates() -> list[dict[str, str]]:
    return list_templates()


@app.get("/workflows")
def workflows_history(db: Session = Depends(get_session)) -> list[dict[str, str]]:
    result = db.execute(select(WorkflowRun))
    runs = result.scalars().all()
    return [
        {"id": r.id, "template": r.template, "status": r.status, "created_at": r.created_at}
        for r in runs
    ]


@app.get("/workflows/{workflow_id}")
def workflow_detail(workflow_id: str, db: Session = Depends(get_session)) -> dict:
    run = db.get(WorkflowRun, workflow_id)
    if not run:
        raise HTTPException(404, "Workflow not found")
    return {
        "id": run.id,
        "template": run.template,
        "status": run.status,
        "result": run.result,
    }


def _run_flow(xml_path: str, params: dict | None, thread_id: str, resume: str | None = None) -> dict:
    with PostgresSaver.from_conn_string(POSTGRES_URL) as saver:
        saver.setup()
        return run_workflow(
            xml_path,
            fn_map=FN_MAP,
            params=params,
            thread_id=thread_id,
            resume=resume,
            checkpointer=saver,
        )


@app.post("/workflows")
def start_workflow(
    data: dict,
    db: Session = Depends(get_session),
) -> dict:
    identifier = data.get("template_name") or data.get("template_id")
    query = data.get("query", "")
    tpl = get_template(identifier)
    if not tpl:
        raise HTTPException(404, "Template not found")
    workflow_id = str(uuid.uuid4())
    result = _run_flow(tpl["path"], {"query": query}, workflow_id)
    status = "WAITING" if "__interrupt__" in result else "COMPLETED"
    run = WorkflowRun(
        id=workflow_id,
        template=tpl["id"],
        thread_id=workflow_id,
        status=status,
        query=query,
        result=result,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"id": run.id, "status": run.status, "result": result}


@app.post("/workflows/{workflow_id}/continue")
def continue_workflow(
    workflow_id: str,
    data: dict,
    db: Session = Depends(get_session),
) -> dict:
    run = db.get(WorkflowRun, workflow_id)
    if not run:
        raise HTTPException(404, "Workflow not found")
    query = data.get("query", "")
    tpl = get_template(run.template)
    resume_payload = json.dumps({"answer": query})
    result = _run_flow(tpl["path"], None, workflow_id, resume=resume_payload)
    run.status = "WAITING" if "__interrupt__" in result else "COMPLETED"
    run.result = result
    db.commit()
    db.refresh(run)
    return {"id": run.id, "status": run.status, "result": result}

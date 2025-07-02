from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from enum import Enum

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
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


class WorkflowStatus(str, Enum):
    WORKING = "WORKING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Pydantic models for request/response validation
class StartWorkflowRequest(BaseModel):
    template_name: str
    query: str = ""


class ContinueWorkflowRequest(BaseModel):
    query: str = ""


class WorkflowResponse(BaseModel):
    id: str
    status: WorkflowStatus
    result: dict


class WorkflowDetail(BaseModel):
    id: str
    template: str
    status: WorkflowStatus
    result: dict


class WorkflowHistory(BaseModel):
    id: str
    template: str
    status: WorkflowStatus
    created_at: str


class TemplateInfo(BaseModel):
    id: str
    name: str
    path: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown
    pass

app = FastAPI(lifespan=lifespan, docs_url="/api/docs")


@app.get("/workflow-templates")
def templates() -> list[TemplateInfo]:
    templates_data = list_templates()
    return [TemplateInfo(**template) for template in templates_data]


@app.get("/workflows")
def workflows_history(db: Session = Depends(get_session)) -> list[WorkflowHistory]:
    result = db.execute(select(WorkflowRun))
    runs = result.scalars().all()
    return [
        WorkflowHistory(
            id=r.id, 
            template=r.template, 
            status=r.status, 
            created_at=str(r.created_at)
        )
        for r in runs
    ]


@app.get("/workflows/{workflow_run_id}")
def workflow_detail(workflow_run_id: str, db: Session = Depends(get_session)) -> WorkflowDetail:
    run = db.get(WorkflowRun, workflow_run_id)
    if not run:
        raise HTTPException(404, "Workflow not found")
    return WorkflowDetail(
        id=run.id,
        template=run.template,
        status=run.status,
        result=run.result,
    )


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
    request: StartWorkflowRequest,
    db: Session = Depends(get_session),
) -> WorkflowResponse:
    tpl = get_template(request.template_name)
    if not tpl:
        raise HTTPException(404, "Template not found")
    workflow_run_id = str(uuid.uuid4())
    result = _run_flow(tpl["path"], {"query": request.query}, workflow_run_id)
    status = WorkflowStatus.WAITING if "__interrupt__" in result else WorkflowStatus.COMPLETED
    run = WorkflowRun(
        id=workflow_run_id,
        template=tpl["id"],
        thread_id=workflow_run_id,
        status=status,
        query=request.query,
        result=result,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return WorkflowResponse(id=run.id, status=run.status, result=result)


@app.post("/workflows/{workflow_run_id}/continue")
def continue_workflow(
    workflow_run_id: str,
    request: ContinueWorkflowRequest,
    db: Session = Depends(get_session),
) -> WorkflowResponse:
    run = db.get(WorkflowRun, workflow_run_id)
    if not run:
        raise HTTPException(404, "Workflow not found")
    tpl = get_template(run.template)
    resume_payload = json.dumps({"answer": request.query})
    result = _run_flow(tpl["path"], None, workflow_run_id, resume=resume_payload)
    run.status = WorkflowStatus.WAITING if "__interrupt__" in result else WorkflowStatus.COMPLETED
    run.result = result
    db.commit()
    db.refresh(run)
    return WorkflowResponse(id=run.id, status=run.status, result=result)

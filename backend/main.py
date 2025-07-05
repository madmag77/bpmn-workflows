from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from enum import Enum

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

import steps.deepresearch_functions as drf

from backend.database import init_db, get_session
from backend.models import WorkflowRun
from backend.workflow_loader import list_templates, get_template
from fastapi_mcp import FastApiMCP

POSTGRES_URL = os.getenv("DATABASE_URL")

FN_MAP = {name: getattr(drf, name) for name in dir(drf) if not name.startswith("_")}


class WorkflowStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    NEEDS_INPUT = "needs_input"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


# Pydantic models for request/response validation
class StartWorkflowRequest(BaseModel):
    template_name: str
    query: str = ""


class ContinueWorkflowRequest(BaseModel):
    query: str = ""


class WorkflowResponse(BaseModel):
    id: str
    status: WorkflowStatus
    result: dict = {}


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


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)


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
            template=r.graph_name,
            status=r.state,
            created_at=str(r.created_at),
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
        template=run.graph_name,
        status=run.state,
        result=run.result,
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
    run = WorkflowRun(
        id=workflow_run_id,
        graph_name=tpl["id"],
        thread_id=workflow_run_id,
        state=WorkflowStatus.QUEUED,
        query=request.query,
        result={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return WorkflowResponse(id=run.id, status=run.state, result={})


@app.post("/workflows/{workflow_run_id}/continue")
def continue_workflow(
    workflow_run_id: str,
    request: ContinueWorkflowRequest,
    db: Session = Depends(get_session),
) -> WorkflowResponse:
    run = db.get(WorkflowRun, workflow_run_id)
    if not run:
        raise HTTPException(404, "Workflow not found")
    if run.state != WorkflowStatus.NEEDS_INPUT:
        raise HTTPException(400, "Workflow not waiting for input")
    run.resume_payload = json.dumps({"answer": request.query})
    run.state = WorkflowStatus.QUEUED
    db.commit()
    db.refresh(run)
    return WorkflowResponse(id=run.id, status=run.state, result=run.result or {})

mcp = FastApiMCP(app, name="workflow runner")
mcp.mount()
import os
import json
import asyncio
from typing import Any, Dict

import asyncpg
from langgraph.checkpoint.postgres import PostgresSaver

from bpmn_workflows.run_bpmn_workflow import run_workflow
from backend.workflow_loader import get_template
import steps.deepresearch_functions as drf

FN_MAP = {name: getattr(drf, name) for name in dir(drf) if not name.startswith("_")}

async def claim_job(pool: asyncpg.pool.Pool, worker_id: str) -> Dict[str, Any] | None:
    async with pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow(
            """
            WITH next AS (
                SELECT id
                FROM workflow_runs
                WHERE state = 'queued'
                ORDER BY id
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            UPDATE workflow_runs
            SET state='running',
                worker_id = $1,
                started_at = now(),
                heartbeat_at = now(),
                attempt = attempt + 1
            FROM next
            WHERE workflow_runs.id = next.id
            RETURNING workflow_runs.*;
            """,
            worker_id,
        )
    return dict(row) if row else None

async def set_state(
    pool: asyncpg.pool.Pool,
    job_id: str,
    new_state: str,
    result: Dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE workflow_runs
            SET state = $2,
                heartbeat_at = CASE WHEN $2='running' THEN now() ELSE heartbeat_at END,
                finished_at = CASE WHEN $2 IN ('succeeded','failed') THEN now() END,
                error = $3,
                result = COALESCE($4, result)
            WHERE id = $1
            """,
            job_id,
            new_state,
            error,
            json.dumps(result) if result is not None else None,
        )

async def run_langgraph(job: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    tpl = get_template(job["graph_name"])
    if not tpl:
        raise ValueError("Template not found")
    params = {"query": job.get("query", "")}
    resume = job.get("resume_payload")
    if resume:
        params = None
    with PostgresSaver.from_conn_string(os.getenv("DATABASE_URL")) as saver:
        saver.setup()
        result = await asyncio.to_thread(
            run_workflow,
            tpl["path"],
            fn_map=FN_MAP,
            params=params,
            thread_id=job["id"],
            resume=resume,
            checkpointer=saver,
        )
    state = "needs_input" if "__interrupt__" in result else "succeeded"
    return state, result

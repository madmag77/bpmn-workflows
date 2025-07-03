import asyncio
import os
import uuid
import asyncpg

from worker.db import claim_job, run_langgraph, set_state

CONCURRENCY = int(os.getenv("WORKERS", 4))


async def worker(pool: asyncpg.pool.Pool, wid: str) -> None:
    while True:
        job = await claim_job(pool, wid)
        if job is None:
            await asyncio.sleep(10)
            continue
        try:
            new_state, result = await run_langgraph(job)
            await set_state(pool, job["id"], new_state, result=result)
        except Exception as exc:  # pragma: no cover - errors in worker
            await set_state(pool, job["id"], "failed", error=str(exc))


async def main() -> None:
    pool = await asyncpg.create_pool(dsn=os.getenv("DATABASE_URL"))
    tasks = [asyncio.create_task(worker(pool, f"w{uuid.uuid4()}")) for _ in range(CONCURRENCY)]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

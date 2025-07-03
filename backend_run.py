import asyncio
import uvicorn
from worker.worker_pool import main as worker_main

async def run_backend():
    """Run the FastAPI backend server"""
    config = uvicorn.Config("backend.main:app", host="0.0.0.0", port=8000, reload=False)
    server = uvicorn.Server(config)
    await server.serve()

async def run_services():
    """Run both backend and worker pool concurrently"""
    # Create tasks for both services
    backend_task = asyncio.create_task(run_backend())
    worker_task = asyncio.create_task(worker_main())
    
    # Run both tasks concurrently
    await asyncio.gather(backend_task, worker_task)

if __name__ == "__main__":
    print("Starting backend server and worker pool...")
    asyncio.run(run_services())

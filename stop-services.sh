#!/bin/bash

echo "Stopping services..."

# Stop the container
echo "Stopping awsl-postgres container..."
container stop awsl-postgres

# Kill any remaining processes
echo "Killing any remaining backend/frontend processes..."
pkill -f "python backend_run.py"
pkill -f "npm run dev"

echo "All services stopped."

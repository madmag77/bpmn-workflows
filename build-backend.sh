#!/bin/bash

set -e

echo "🔨 Building backend binary with PyInstaller..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ backend_run.spec

# Find PostgreSQL library path
POSTGRES_LIB=$(brew --prefix postgresql@15)/lib
if [ ! -d "$POSTGRES_LIB" ]; then
    POSTGRES_LIB=$(brew --prefix postgresql)/lib
fi

echo "🔍 Using PostgreSQL libraries from: $POSTGRES_LIB"

# Build with PyInstaller
echo "🏗️  Running PyInstaller..."
pyinstaller --onefile \
    --name backend_run \
    --additional-hooks-dir hooks \
    --add-data "backend:backend" \
    --add-data "worker:worker" \
    --add-data "workflow_definitions:workflow_definitions" \
    --add-data "prompts:prompts" \
    --add-data "steps:steps" \
    --add-data "awsl:awsl" \
    --add-data "bpmn_workflows:bpmn_workflows" \
    --add-data "bpmn_ext:bpmn_ext" \
    --add-data "components:components" \
    --add-binary "$POSTGRES_LIB/libpq.*.dylib:." \
    --hidden-import sqlalchemy.dialects.postgresql \
    --hidden-import psycopg2 \
    --hidden-import psycopg \
    --hidden-import psycopg.pq \
    --hidden-import psycopg._pq \
    --hidden-import asyncpg \
    --hidden-import backend.main \
    --hidden-import worker.worker_pool \
    --hidden-import pdf2image \
    --hidden-import PIL \
    --hidden-import PIL.Image \
    --hidden-import langchain_openai \
    --collect-all psycopg \
    backend_run.py

echo "✅ Backend binary built successfully!"
echo "📍 Binary location: ./dist/backend_run"
echo "🧪 Test with: ./dist/backend_run"

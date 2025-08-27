#!/bin/bash

set -e

echo "🚀 Starting Workflows system with Apple Container..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if container exists (running or stopped)
check_container() {
    container ls --format table | grep "$1" 2>/dev/null
}

# Function to stop and remove container if it exists
cleanup_container() {
    if check_container "$1"; then
        echo -e "${YELLOW}Stopping and removing existing container: $1${NC}"
        container stop "$1" >/dev/null 2>&1 || true
        container rm "$1" >/dev/null 2>&1 || true
        container images rm "$1" >/dev/null 2>&1 || true
    fi
}

# Cleanup existing containers
echo -e "${BLUE}🧹 Cleaning up existing containers...${NC}"
cleanup_container "postgres"
cleanup_container "awsl-postgres"
cleanup_container "awsl-backend"
cleanup_container "awsl-frontend"

# Build images if they don't exist
echo -e "${BLUE}🔨 Building container images...${NC}"

# Build backend
echo -e "${YELLOW}Building backend image...${NC}"
container build -t awsl-backend -f Dockerfile.backend . >/dev/null

# Build frontend
echo -e "${YELLOW}Building frontend image...${NC}"
container build -t awsl-frontend -f Dockerfile.frontend . >/dev/null

# Start PostgreSQL
echo -e "${BLUE}🐘 Starting PostgreSQL...${NC}"
container run -d \
  --name awsl-postgres \
  -e POSTGRES_DB=workflows \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
sleep 10

# Get PostgreSQL container IP using container ls
echo -e "${YELLOW}🔍 Getting PostgreSQL container IP...${NC}"
POSTGRES_IP=$(container ls --format table | grep "postgres" | awk '{print $NF}')
if [ -z "$POSTGRES_IP" ]; then
    echo -e "${YELLOW}⚠️  Could not find PostgreSQL container IP, using localhost${NC}"
    POSTGRES_IP="localhost"
fi
echo -e "${GREEN}PostgreSQL IP: ${POSTGRES_IP}${NC}"

# Start backend
echo -e "${BLUE}⚙️  Starting Backend...${NC}"
container run -d \
  --name awsl-backend \
  -e DATABASE_URL=postgresql://postgres:postgres@${POSTGRES_IP}:5432/workflows \
  -v "$(pwd)/workflows:/app/workflows" \
  -v "$(pwd)/awsl:/app/awsl" \
  -v "$(pwd)/steps:/app/steps" \
  -v "$(pwd)/prompts:/app/prompts" \
  -p 8000:8000 \
  awsl-backend

# Wait for backend to be ready
echo -e "${YELLOW}⏳ Waiting for backend to be ready...${NC}"
sleep 5

# Get Backend container IP
echo -e "${YELLOW}🔍 Getting Backend container IP...${NC}"
BACKEND_IP=$(container ls --format table | grep "awsl-backend" | awk '{print $NF}')
if [ -z "$BACKEND_IP" ]; then
    echo -e "${YELLOW}⚠️  Could not find Backend container IP, using localhost${NC}"
    BACKEND_IP="localhost"
fi
echo -e "${GREEN}Backend IP: ${BACKEND_IP}${NC}"

# Start frontend
echo -e "${BLUE}🌐 Starting Frontend...${NC}"
container run -d \
  --name awsl-frontend \
  -e VITE_API_BASE_URL=${BACKEND_IP}:8000 \
  -p 3000:80 \
  awsl-frontend

# Wait for frontend to be ready and get its IP
echo -e "${YELLOW}⏳ Waiting for frontend to be ready...${NC}"
sleep 3

# Get Frontend container IP
echo -e "${YELLOW}🔍 Getting Frontend container IP...${NC}"
FRONTEND_IP=$(container ls --format table | grep "awsl-frontend" | awk '{print $NF}')
if [ -z "$FRONTEND_IP" ]; then
    echo -e "${YELLOW}⚠️  Could not find Frontend container IP, using localhost${NC}"
    FRONTEND_IP="localhost"
fi
echo -e "${GREEN}Frontend IP: ${FRONTEND_IP}${NC}"

echo -e "${GREEN}✅ All containers started successfully!${NC}"
echo ""
echo -e "${BLUE}📊 Container Status:${NC}"
container list --format table

echo ""
echo -e "${GREEN}🌍 Access your application:${NC}"
echo -e "  ${GREEN}🌐 Frontend (Browser): ${BLUE}http://${FRONTEND_IP}${NC}"
echo -e "  Backend API:  ${BLUE}${BACKEND_IP}:8000${NC}"
echo -e "  PostgreSQL: ${BLUE}${POSTGRES_IP}:5432${NC}"

echo ""
echo -e "${YELLOW}💡 Useful commands:${NC}"
echo -e "  View logs: ${BLUE}container logs <container_name>${NC}"
echo -e "  Stop all: ${BLUE}./stop-containers.sh${NC}"
echo -e "  Container status: ${BLUE}container ps${NC}"

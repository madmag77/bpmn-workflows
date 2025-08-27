#!/bin/bash

# Removed set -e to allow graceful error handling

echo "🛑 Stopping AWSL Workflows system..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color


# Function to stop and remove container
stop_container() {
        echo -e "${YELLOW}Stopping $1...${NC}"
        
        # Stop container (ignore errors if not running)
        if container stop "$1" 2>/dev/null; then
                echo -e "${BLUE}  Container $1 stopped${NC}"
        else
                echo -e "${YELLOW}  Container $1 was not running or doesn't exist${NC}"
        fi
        
        # Remove container (ignore errors if doesn't exist)
        if container rm "$1" 2>/dev/null; then
                echo -e "${BLUE}  Container $1 removed${NC}"
        else
                echo -e "${YELLOW}  Container $1 was already removed or doesn't exist${NC}"
        fi
        
        # Remove image (ignore errors if doesn't exist)
        if container images rm "$1" 2>/dev/null; then
                echo -e "${BLUE}  Image $1 removed${NC}"
        else
                echo -e "${YELLOW}  Image $1 was already removed or doesn't exist${NC}"
        fi
        
        echo -e "${GREEN}✅ $1 cleanup completed${NC}"
}

# Stop containers in reverse order
stop_container "awsl-frontend"
stop_container "awsl-backend" 
stop_container "awsl-postgres"
stop_container "postgres"

echo ""
echo -e "${GREEN}✅ All containers stopped successfully!${NC}"


#!/bin/bash

# Network Monitor Management Script
# Source this file to get convenient functions for managing the netmon application
#
# Usage:
#   source netmon.sh
#   netmon_start          # Start the application
#   netmon_stop           # Stop the application  
#   netmon_restart        # Restart the application
#   netmon_status         # Check if application is running
#   netmon_logs           # View application logs
#   netmon_dashboard      # Open dashboard in browser
#   netmon_data           # Access data management tools

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
if [[ -n "${BASH_SOURCE[0]}" ]]; then
    NETMON_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
else
    NETMON_DIR="$(pwd)"
fi
VENV_PATH="$NETMON_DIR/.venv"
PYTHON_PATH="$VENV_PATH/bin/python"
PID_FILE="$NETMON_DIR/.netmon.pid"
LOG_FILE="$NETMON_DIR/app.log"

# Check if we're in the right directory and virtual environment exists
if [[ ! -f "$NETMON_DIR/main.py" ]]; then
    echo -e "${RED}Error: Not in netmon directory or main.py not found${NC}"
    return 1
fi

if [[ ! -d "$VENV_PATH" ]]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_PATH${NC}"
    return 1
fi

# Function to check if application is running
netmon_status() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN}✓ NetMon is running (PID: $pid)${NC}"
            echo -e "${BLUE}  Dashboard: http://localhost:8000${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠ PID file exists but process not running${NC}"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        echo -e "${RED}✗ NetMon is not running${NC}"
        return 1
    fi
}

# Function to start the application
netmon_start() {
    if netmon_status >/dev/null 2>&1; then
        echo -e "${YELLOW}NetMon is already running${NC}"
        netmon_status
        return 0
    fi

    echo -e "${BLUE}Starting NetMon...${NC}"
    cd "$NETMON_DIR"
    
    # Activate virtual environment and start the application
    nohup "$PYTHON_PATH" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo $pid > "$PID_FILE"
    
    # Wait a moment and check if it started successfully
    sleep 2
    if kill -0 "$pid" 2>/dev/null; then
        echo -e "${GREEN}✓ NetMon started successfully${NC}"
        netmon_status
    else
        echo -e "${RED}✗ Failed to start NetMon${NC}"
        echo -e "${YELLOW}Check logs with: netmon_logs${NC}"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Function to stop the application
netmon_stop() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${BLUE}Stopping NetMon (PID: $pid)...${NC}"
            kill "$pid"
            sleep 2
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${YELLOW}Force killing NetMon...${NC}"
                kill -9 "$pid"
            fi
            
            rm -f "$PID_FILE"
            echo -e "${GREEN}✓ NetMon stopped${NC}"
        else
            echo -e "${YELLOW}PID file exists but process not running${NC}"
            rm -f "$PID_FILE"
        fi
    else
        echo -e "${RED}NetMon is not running${NC}"
    fi
    
    # Also kill any remaining uvicorn processes
    pkill -f "uvicorn main:app" 2>/dev/null && echo -e "${YELLOW}Killed remaining uvicorn processes${NC}"
}

# Function to restart the application
netmon_restart() {
    echo -e "${BLUE}Restarting NetMon...${NC}"
    netmon_stop
    sleep 1
    netmon_start
}

# Function to view logs
netmon_logs() {
    if [[ -f "$LOG_FILE" ]]; then
        echo -e "${BLUE}NetMon application logs (press Ctrl+C to exit):${NC}"
        tail -f "$LOG_FILE"
    else
        echo -e "${YELLOW}No log file found${NC}"
    fi
}

# Function to open dashboard
netmon_dashboard() {
    if netmon_status >/dev/null 2>&1; then
        echo -e "${BLUE}Opening NetMon dashboard...${NC}"
        if command -v xdg-open >/dev/null 2>&1; then
            xdg-open "http://localhost:8000" 2>/dev/null
        elif command -v open >/dev/null 2>&1; then
            open "http://localhost:8000"
        else
            echo -e "${YELLOW}Please open http://localhost:8000 in your browser${NC}"
        fi
    else
        echo -e "${RED}NetMon is not running. Start it with: netmon_start${NC}"
    fi
}

# Function to access data management
netmon_data() {
    cd "$NETMON_DIR"
    echo -e "${BLUE}NetMon Data Management${NC}"
    echo "Available commands:"
    echo "  list-networks    - List all available networks"
    echo "  list-data        - List data for current network"
    echo "  export-csv       - Export data to CSV"
    echo "  cleanup-old      - Clean up old data"
    echo ""
    echo "Usage: $PYTHON_PATH manage_data.py [command] [options]"
    echo ""
    echo -e "${YELLOW}Example: $PYTHON_PATH manage_data.py list-data --days 7${NC}"
}

# Function to install/update dependencies
netmon_deps() {
    cd "$NETMON_DIR"
    echo -e "${BLUE}Installing/updating NetMon dependencies...${NC}"
    "$PYTHON_PATH" -m pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies updated${NC}"
}

# Function to run database migrations (if using Prisma)
netmon_migrate() {
    cd "$NETMON_DIR"
    echo -e "${BLUE}Running database migrations...${NC}"
    # Add migration commands here if needed
    echo -e "${YELLOW}No migrations configured yet${NC}"
}

# Function to show help
netmon_help() {
    echo -e "${BLUE}NetMon Management Commands:${NC}"
    echo ""
    echo -e "${GREEN}Application Control:${NC}"
    echo "  netmon_start       - Start the NetMon application"
    echo "  netmon_stop        - Stop the NetMon application"
    echo "  netmon_restart     - Restart the NetMon application"
    echo "  netmon_status      - Check if NetMon is running"
    echo ""
    echo -e "${GREEN}Monitoring & Logs:${NC}"
    echo "  netmon_logs        - View application logs (real-time)"
    echo "  netmon_dashboard   - Open dashboard in browser"
    echo ""
    echo -e "${GREEN}Data Management:${NC}"
    echo "  netmon_data        - Access data management tools"
    echo ""
    echo -e "${GREEN}Maintenance:${NC}"
    echo "  netmon_deps        - Install/update dependencies"
    echo "  netmon_migrate     - Run database migrations"
    echo "  netmon_help        - Show this help"
    echo ""
    echo -e "${YELLOW}Quick start: netmon_start${NC}"
}

# Set up aliases for convenience
alias nm_start='netmon_start'
alias nm_stop='netmon_stop'
alias nm_restart='netmon_restart'
alias nm_status='netmon_status'
alias nm_logs='netmon_logs'
alias nm_dash='netmon_dashboard'
alias nm_help='netmon_help'

# Show status on source
echo -e "${BLUE}NetMon management functions loaded${NC}"
echo -e "${YELLOW}Type 'netmon_help' for available commands${NC}"
netmon_status 2>/dev/null || echo -e "${YELLOW}Use 'netmon_start' to start the application${NC}"

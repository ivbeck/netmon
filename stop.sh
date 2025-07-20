#!/bin/bash

# Simple NetMon Stop Script
# This script can be run directly to stop NetMon

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Source the management functions
source "$SCRIPT_DIR/netmon.sh"

# Stop the application
netmon_stop

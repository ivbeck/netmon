#!/bin/bash

# Simple NetMon Starter Script
# This script can be run directly to start NetMon

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Source the management functions
source "$SCRIPT_DIR/netmon.sh"

# Start the application
netmon_start

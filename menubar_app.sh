#!/bin/bash

# Accountability App - Menu Bar Only Launcher
# This script launches the Accountability app as a menu bar only application on macOS

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Set environment variables for menu bar only application
export LSUIElement=1

# Run the application with Python
/usr/bin/env python3 main.py

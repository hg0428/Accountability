#!/bin/bash

# Run the Accountability app as a background application (no dock icon)
cd "$(dirname "$0")"
export LSUIElement=1
python3 main.py

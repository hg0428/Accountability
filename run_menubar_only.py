#!/usr/bin/env python3
"""
Special launcher for Accountability App that runs as a menu bar only application on macOS.
"""

import sys
import os
import subprocess
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QProcess

def main():
    """
    Launch the Accountability app as a menu bar only application on macOS.
    """
    if sys.platform != 'darwin':
        print("This launcher is only for macOS.")
        return 1
    
    # Get the path to the main.py file
    main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    
    # Create a process to run the main script with LSUIElement=1
    env = os.environ.copy()
    env["LSUIElement"] = "1"
    
    # Use subprocess to launch the app with the LSUIElement flag
    process = subprocess.Popen(
        ["python3", main_script],
        env=env,
        start_new_session=True  # This detaches the process
    )
    
    # Exit this launcher script
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Accountability App - Main Entry Point
An application that reminds users hourly to record their activities.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QIcon
from accountability.app import AccountabilityApp

def main():
    """Initialize and run the Accountability application."""
    # Set the application to be a menu bar only app (no dock icon)
    if sys.platform == 'darwin':
        # This must be set before creating QApplication
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_PluginApplication, True)
        os.environ['LSUIElement'] = '1'  # Hide from dock on macOS
        
    app = QApplication(sys.argv)
    app.setApplicationName("Accountability")
    app.setQuitOnLastWindowClosed(False)  # Allow running in background
    
    # Set application icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                           "accountability", "ui", "resources", "logo.png")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    
    # Initialize the main application
    accountability_app = AccountabilityApp()
    accountability_app.start()
    
    # Start the event loop
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

"""
Main Application Module for Accountability App.
"""

import sys
import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox, QLabel, QApplication
from PyQt6.QtGui import QIcon, QColor, QPixmap
from PyQt6.QtCore import QTimer, Qt, QDateTime, QTime

from accountability.scheduler import ActivityScheduler
from accountability.database import Database
from accountability.ui.main_window import MainWindow
from accountability.ui.reminder import ReminderDialog


class AccountabilityApp:
    """Main application class for Accountability app."""

    def __init__(self):
        """Initialize the application components."""
        # Initialize database connection
        self.db = Database()
        self.db.initialize()

        # Initialize the scheduler
        self.scheduler = ActivityScheduler(self.db)

        # Connect to the scheduler's signals
        self.scheduler.missed_hours_changed.connect(self.on_missed_hours_changed)

        # Create UI components
        self.main_window = MainWindow(self.db, self.scheduler)

        # Setup tray icon
        self.setup_tray_icon()

        # Timer for checking hourly notifications
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_schedule)

        # Timer for checking at the top of each hour
        self.hourly_timer = QTimer()
        self.hourly_timer.timeout.connect(self.setup_next_hour_timer)

        # Flag to prevent multiple reminders
        self.reminder_showing = False

    def start(self):
        """Start the application and initialize components."""
        # Load initial data and settings
        self.scheduler.initialize()

        # Start timer to check for scheduled reminders every minute
        self.check_timer.start(60000)  # Check every minute

        # Set up timer for the next hour change
        self.setup_next_hour_timer()

        # Show the main window on startup
        self.main_window.show()

        # Show reminder for any missed hours on startup
        self.check_schedule()

    def setup_next_hour_timer(self):
        """Set up a timer to trigger at the top of the next hour."""
        now = QDateTime.currentDateTime()
        next_hour = now.addSecs(3600)  # Add one hour
        next_hour_time = QDateTime(
            next_hour.date(), QTime(next_hour.time().hour(), 0, 0)
        )

        # Calculate milliseconds until the next hour
        msecs_to_next_hour = now.msecsTo(next_hour_time)

        # If we're already at the top of the hour or very close, add an hour
        if msecs_to_next_hour <= 1000:
            msecs_to_next_hour += 3600000  # Add an hour in milliseconds

        # Set the timer for the next hour
        self.hourly_timer.start(msecs_to_next_hour)

        # Also trigger a check at the top of the hour
        self.check_schedule(force=True)

    def check_schedule(self, force=False):
        """
        Check if it's time to show a reminder.

        Args:
            force: If True, force a check regardless of timing
        """
        # Don't show another reminder if one is already showing
        if self.reminder_showing:
            return

        # Get missed hours
        missed_hours = self.scheduler.get_missed_hours()

        # If we have missed hours and either force is True or it's a new hour, show the reminder
        if missed_hours and (force or self.is_new_hour()):
            self.show_reminder(missed_hours)

    def is_new_hour(self):
        """Check if we've entered a new hour since the last check."""
        now = QDateTime.currentDateTime()
        current_minute = now.time().minute()

        # Consider it a new hour if we're within the first 5 minutes of the hour
        return current_minute < 5

    def show_reminder(self, hours):
        """Show the reminder dialog for the specified hours."""
        self.reminder_showing = True
        dialog = ReminderDialog(hours, self.db, self.scheduler)
        dialog.finished.connect(self.on_reminder_closed)

        # Show notification if system supports it
        if QSystemTrayIcon.supportsMessages():
            self.tray_icon.showMessage(
                "Accountability Reminder",
                f"You have {len(hours)} hour(s) to record",
                QSystemTrayIcon.MessageIcon.Information,
                5000,  # Show for 5 seconds
            )

        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def on_reminder_closed(self, result):
        """Handle reminder dialog being closed."""
        self.reminder_showing = False

        # Refresh data even if the dialog was cancelled
        self.scheduler.refresh_schedule()
        self.main_window.refresh_data()

    def on_missed_hours_changed(self, count):
        """Handle changes to the missed hours count."""
        # Update the tray icon tooltip
        if count > 0:
            self.tray_icon.setToolTip(f"Accountability App - {count} missed hour(s)")

            # Change the tray icon to indicate missed hours
            if count > 0:
                self.set_alert_icon(count)
        else:
            self.tray_icon.setToolTip("Accountability App")
            self.reset_tray_icon()

    def set_alert_icon(self, count):
        """Set the tray icon to an alert state with a count badge."""
        # This is a simple implementation - in a real app you might want to create
        # a proper icon with a badge overlay
        if not hasattr(self, "original_icon"):
            self.original_icon = self.tray_icon.icon()

        # For now, we'll just change the tooltip to indicate missed hours
        self.tray_icon.setToolTip(f"Accountability App - {count} missed hour(s)")

    def reset_tray_icon(self):
        """Reset the tray icon to its normal state."""
        if hasattr(self, "original_icon"):
            self.tray_icon.setIcon(self.original_icon)
        self.tray_icon.setToolTip("Accountability App")

    def setup_tray_icon(self):
        """Set up the system tray icon and menu."""
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.warning(
                None, "System Tray", "System tray is not available on this system."
            )
            return

        # Create tray icon with the custom logo
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                               "ui", "resources", "logo.png")
        print(f"Loading tray icon from: {icon_path}")
        
        # Create a QPixmap from the image file first
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            # Create a smaller version for the tray icon if needed
            if pixmap.width() > 64 or pixmap.height() > 64:
                pixmap = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, 
                                     Qt.TransformationMode.SmoothTransformation)
            
            icon = QIcon(pixmap)
            print(f"Tray icon loaded successfully, size: {pixmap.width()}x{pixmap.height()}")
        else:
            print("Failed to load tray icon, using fallback")
            icon = QIcon.fromTheme("appointment-soon")
            if icon.isNull():
                icon = QIcon.fromTheme("accessories-calculator")
                if icon.isNull():
                    icon = QIcon.fromTheme("dialog-information")

        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Accountability App")

        # Create tray menu
        tray_menu = QMenu()

        open_action = tray_menu.addAction("Open")
        open_action.triggered.connect(self.main_window.show)

        history_action = tray_menu.addAction("View History")
        history_action.triggered.connect(self.main_window.show_history)

        check_now_action = tray_menu.addAction("Check Missed Hours")
        check_now_action.triggered.connect(lambda: self.check_schedule(force=True))

        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.quit)

        # Set the menu and show the icon
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # Connect the activated signal to handle tray icon clicks
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def on_tray_icon_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click - show/hide main window
            if self.main_window.isVisible():
                self.main_window.hide()
            else:
                self.main_window.show()
                self.main_window.raise_()
                self.main_window.activateWindow()

    def quit(self):
        """Quit the application cleanly."""
        self.db.close()
        self.tray_icon.hide()
        sys.exit(0)

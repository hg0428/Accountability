"""
Main Application Module for Accountability App.
"""

import sys
import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox, QLabel, QApplication
from PyQt6.QtGui import QIcon, QColor, QPixmap, QAction
from PyQt6.QtCore import QTimer, Qt, QDateTime, QTime

from accountability.scheduler import ActivityScheduler
from accountability.database import Database
from accountability.ui.main_window import MainWindow
from accountability.ui.reminder import ReminderDialog


class AccountabilityApp:
    """Main application class for Accountability app."""

    def __init__(self, app=None):
        """Initialize the application components."""
        # Store the QApplication instance
        self.app = app

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
            self.show_reminder_for_hours(missed_hours)

    def is_new_hour(self):
        """Check if we've entered a new hour since the last check."""
        now = QDateTime.currentDateTime()
        current_minute = now.time().minute()

        # Consider it a new hour if we're within the first 5 minutes of the hour
        return current_minute < 5

    def show_reminder_for_hours(self, hours):
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
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("System tray not available")
            return

        # Create tray icon with the custom logo
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "ui", "resources", "logo.png"
        )
        print(f"Loading tray icon from: {icon_path}")

        # Create a QPixmap from the image file first
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            # Scale down if needed
            if pixmap.width() > 64 or pixmap.height() > 64:
                pixmap = pixmap.scaled(
                    64,
                    64,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

            icon = QIcon(pixmap)
            print(
                f"Tray icon loaded successfully, size: {pixmap.width()}x{pixmap.height()}"
            )
        else:
            print("Failed to load tray icon, using fallback")
            icon = QIcon.fromTheme("appointment-soon")

        # Create the tray icon with the application as parent
        self.tray_icon = QSystemTrayIcon(icon, self.app)
        self.tray_icon.setToolTip("Accountability")

        # Create menu without parent, but store as instance variable
        self.tray_menu = QMenu()

        # Create actions parented to the menu
        self.open_action = QAction("Open", self.tray_menu)
        self.open_action.triggered.connect(self.show_main_window)

        self.record_action = QAction("Record Activity", self.tray_menu)
        self.record_action.triggered.connect(self.main_window.on_edit_current_activity)
        
        # Add export action
        self.export_action = QAction("Export Data", self.tray_menu)
        self.export_action.triggered.connect(self.export_data)

        self.quit_action = QAction("Quit", self.tray_menu)
        self.quit_action.triggered.connect(self.quit)

        # Add actions to menu
        self.tray_menu.addAction(self.open_action)
        self.tray_menu.addAction(self.record_action)
        self.tray_menu.addAction(self.export_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.quit_action)

        # Set menu to tray icon
        self.tray_icon.setContextMenu(self.tray_menu)

        # Show the tray icon
        self.tray_icon.show()

        # We don't want the main window to show on tray icon click
        # but we'll keep this method available for future use
        # self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def on_tray_icon_activated(self, reason):
        """Handle tray icon activation."""
        # Disabled for now - uncomment if you want the tray icon to do something on click
        # if reason == QSystemTrayIcon.ActivationReason.Trigger:
        #     self.show_main_window()
        pass

    def show_main_window(self):
        """Show and activate the main window."""
        if not self.main_window.isVisible():
            self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def show_reminder(self):
        """Show the activity reminder dialog for the current hour."""
        current_hour = QDateTime.currentDateTime().toPyDateTime()
        hours = [current_hour]
        self.show_reminder_for_hours(hours)

    def quit(self):
        """Quit the application cleanly."""
        self.db.close()
        self.tray_icon.hide()
        sys.exit(0)

    def export_data(self):
        """Export activity data to a file."""
        # First show the main window in case it's hidden
        self.show_main_window()
        
        # Import necessary modules
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        import json
        import os
        from datetime import datetime, timedelta
        
        # Ask user for file location and format
        file_path, selected_filter = QFileDialog.getSaveFileName(
            None,
            "Export Activity Data",
            os.path.expanduser("~/activities_export.json"),
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)",
        )

        if not file_path:
            return  # User cancelled

        try:
            success = False

            # Use the database's export methods if available
            if hasattr(self.db, "export_activities_to_json") and hasattr(
                self.db, "export_activities_to_text"
            ):
                if file_path.lower().endswith(".json"):
                    success = self.db.export_activities_to_json(file_path)
                else:
                    success = self.db.export_activities_to_text(file_path)
            else:
                # Fallback to our own implementation
                # Get all activities from the database
                all_activities = []

                # Get activities for the last year as a reasonable default
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)

                current_date = start_date
                while current_date <= end_date:
                    day_start = datetime(
                        current_date.year, current_date.month, current_date.day
                    )
                    day_activities = self.db.get_activities_for_day(day_start)
                    all_activities.extend(day_activities)
                    current_date += timedelta(days=1)

                activities_to_export = all_activities
                date_range = "Last Year"

                # Format the activities for export
                formatted_activities = []
                for activity in activities_to_export:
                    formatted_activities.append(
                        {
                            "date": activity["hour"].strftime("%Y-%m-%d"),
                            "time": activity["hour"].strftime("%H:%M"),
                            "activity": activity["activity"],
                        }
                    )

                # Prepare the export data
                export_data = {
                    "date_range": date_range,
                    "export_date": datetime.now().isoformat(),
                    "activities": formatted_activities,
                }

                # Export based on file extension
                if file_path.lower().endswith(".json"):
                    # JSON export
                    with open(file_path, "w") as f:
                        json.dump(export_data, f, indent=2)
                    success = True
                else:
                    # Text export
                    with open(file_path, "w") as f:
                        f.write(f"Activity Export - {date_range}\n")
                        f.write(
                            f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        )

                        # Group by date
                        activities_by_date = {}
                        for activity in formatted_activities:
                            date = activity["date"]
                            if date not in activities_by_date:
                                activities_by_date[date] = []
                            activities_by_date[date].append(activity)

                        # Write each date's activities
                        for date, activities in sorted(activities_by_date.items()):
                            f.write(f"=== {date} ===\n")
                            for activity in sorted(activities, key=lambda x: x["time"]):
                                f.write(f"{activity['time']}: {activity['activity']}\n")
                            f.write("\n")
                    success = True

            if success:
                QMessageBox.information(
                    None,
                    "Export Successful",
                    f"Successfully exported activities to {file_path}",
                )
            else:
                QMessageBox.warning(
                    None,
                    "Export Warning",
                    f"The export may not have completed successfully. Please check the file at {file_path}",
                )

        except Exception as e:
            QMessageBox.critical(
                None, "Export Error", f"An error occurred during export: {str(e)}"
            )

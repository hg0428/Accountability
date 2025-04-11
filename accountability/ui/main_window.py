"""
Main Window UI Module for Accountability App.
Provides the primary interface for viewing activity history.
"""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCalendarWidget,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QTextEdit,
    QFrame,
    QSplitter,
    QScrollArea,
    QAbstractItemView,
    QDialog,
    QMessageBox,
    QComboBox,
    QGroupBox,
    QPushButton,
    QGridLayout,
    QSizePolicy,
    QDialogButtonBox,
)
from PyQt6.QtCore import QTime, Qt, QDate, pyqtSlot, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap

from accountability.utils.time_utils import format_hour_range
from .reminder import ReminderDialog
from .analysis_widget import AnalysisWidget


class ActivityInputDialog(QDialog):
    """Dialog for entering or editing an activity."""

    def __init__(self, hour=None, existing_text="", parent=None):
        """Initialize the dialog."""
        super().__init__(parent)

        self.hour = hour
        self.activity_text = existing_text

        self.setWindowTitle("Activity Entry")
        self.setMinimumWidth(400)

        # Load stylesheet
        self.load_stylesheet()

        self.init_ui()

    def init_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Hour display if provided
        if self.hour:
            hour_label = QLabel(f"Time: {format_hour_range(self.hour)}")
            hour_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(hour_label)

        # Activity input
        layout.addWidget(QLabel("Activity:"))
        self.activity_input = QTextEdit()
        self.activity_input.setPlaceholderText("What were you doing during this time?")
        self.activity_input.setText(self.activity_text)
        layout.addWidget(self.activity_input)

        # Common activities (could be populated from frequently used activities)
        common_group = QGroupBox("Quick Select")
        common_layout = QGridLayout()

        common_activities = [
            "Working",
            "Meeting",
            "Lunch",
            "Break",
            "Exercise",
            "Reading",
            "Learning",
            "Sleeping",
        ]

        row, col = 0, 0
        for activity in common_activities:
            btn = QPushButton(activity)
            btn.clicked.connect(
                lambda checked, text=activity: self.activity_input.setText(text)
            )
            common_layout.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        common_group.setLayout(common_layout)
        layout.addWidget(common_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_stylesheet(self):
        """Load the application stylesheet."""
        try:
            import os

            style_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "resources", "style.qss"
            )
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Error loading stylesheet: {e}")

    def get_activity_text(self):
        """Get the entered activity text."""
        return self.activity_input.toPlainText().strip()


class DailySummaryWidget(QWidget):
    """Widget for displaying a summary of the day's activities."""

    def __init__(self, database, date=None, parent=None):
        """Initialize the summary widget."""
        super().__init__(parent)

        self.db = database
        self.date = date or datetime.now().date()

        self.init_ui()

    def init_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Date display
        self.date_label = QLabel()
        self.date_label.setObjectName("sectionTitle")
        layout.addWidget(self.date_label)

        # Summary container
        summary_frame = QFrame()
        summary_frame.setObjectName("card")
        summary_layout = QVBoxLayout(summary_frame)

        # Activity summary section
        activity_header = QLabel("Activity Summary")
        activity_header.setObjectName("sectionTitle")
        summary_layout.addWidget(activity_header)

        # Summary text in a styled container
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFrameShape(QFrame.Shape.NoFrame)
        self.summary_text.setStyleSheet(
            """
            QTextEdit {
                background-color: white;
                border: none;
                padding: 10px;
            }
        """
        )
        summary_layout.addWidget(self.summary_text)

        layout.addWidget(summary_frame)

        # Update the display
        self.update_summary()

    def set_date(self, date):
        """Set the date to display summary for."""
        self.date = date
        self.update_summary()

    def update_summary(self):
        """Update the summary display with activities for the current date."""
        # Update date label
        if self.date == datetime.now().date():
            self.date_label.setText("Today's Summary")
        else:
            date_str = self.date.strftime("%A, %B %d, %Y")
            self.date_label.setText(f"Summary for {date_str}")

        # Get activities for the date
        day_start = datetime(self.date.year, self.date.month, self.date.day)
        activities = self.db.get_activities_for_day(day_start)

        if not activities:
            self.summary_text.setHtml("<p>No activities recorded for this date.</p>")
            return

        # Group activities by type
        activity_dict = {}
        for activity in activities:
            text = activity["activity"]
            hour = activity["hour"]

            if text in activity_dict:
                activity_dict[text].append(hour)
            else:
                activity_dict[text] = [hour]

        # Build HTML summary
        html = "<table width='100%' cellspacing='0' cellpadding='5' style='border-collapse: collapse;'>"

        # Table header
        html += "<tr style='background-color: #f8f9fa; font-weight: bold;'>"
        html += "<th align='left' style='padding: 10px; border-bottom: 1px solid #dfe4ea;'>Activity</th>"
        html += "<th align='center' style='padding: 10px; border-bottom: 1px solid #dfe4ea;'>Hours</th>"
        html += "<th align='left' style='padding: 10px; border-bottom: 1px solid #dfe4ea;'>Time Periods</th>"
        html += "</tr>"

        # Sort activities by most time spent
        sorted_activities = sorted(
            activity_dict.items(), key=lambda x: len(x[1]), reverse=True
        )

        # Add rows for each activity
        row_class = ""
        for activity, hours in sorted_activities:
            # Sort hours chronologically
            hours.sort()

            # Format time periods
            time_periods = []
            for hour in hours:
                time_periods.append(format_hour_range(hour))

            # Alternate row colors
            row_class = "background-color: #f8f9fa;" if row_class == "" else ""

            html += f"<tr style='{row_class}'>"
            html += f"<td style='padding: 10px; border-bottom: 1px solid #f1f2f6;'>{activity}</td>"
            html += f"<td align='center' style='padding: 10px; border-bottom: 1px solid #f1f2f6;'>{len(hours)}</td>"
            html += f"<td style='padding: 10px; border-bottom: 1px solid #f1f2f6;'>{', '.join(time_periods)}</td>"
            html += "</tr>"

        html += "</table>"

        self.summary_text.setHtml(html)


class MainWindow(QMainWindow):
    """Main window for the Accountability app."""

    def __init__(self, database, scheduler):
        """Initialize the main window."""
        super().__init__()

        self.db = database
        self.scheduler = scheduler

        self.init_ui()

    def init_ui(self):
        """Set up the user interface."""
        # Set window properties
        self.setWindowTitle("Accountability")
        self.setMinimumSize(900, 600)

        # Load stylesheet
        self.load_stylesheet()

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)

        # Create tabs
        self.setup_daily_tab()
        self.setup_summary_tab()
        self.setup_analysis_tab()

        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)

    def closeEvent(self, event):
        """Override the close event to hide the window instead of closing."""
        event.ignore()  # Prevent the window from actually closing
        self.hide()  # Hide the window

    def load_stylesheet(self):
        """Load the application stylesheet."""
        try:
            import os

            style_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "resources", "style.qss"
            )
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Error loading stylesheet: {e}")

    def setup_daily_tab(self):
        """Set up the daily view tab."""
        daily_tab = QWidget()
        daily_layout = QVBoxLayout(daily_tab)
        daily_layout.setContentsMargins(0, 10, 0, 0)
        daily_layout.setSpacing(15)

        # Create a card-like container for the content
        content_frame = QFrame()
        content_frame.setObjectName("card")
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(20)

        # Left panel - Calendar and navigation
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Date selection label
        date_label = QLabel("Select Date:")
        date_label.setObjectName("sectionTitle")
        left_layout.addWidget(date_label)

        # Calendar widget
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.calendar.setSelectionMode(QCalendarWidget.SelectionMode.SingleSelection)
        self.calendar.clicked.connect(self.on_date_selected)

        # Set today as the selected date
        self.calendar.setSelectedDate(QDate.currentDate())

        left_layout.addWidget(self.calendar)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 10, 0, 0)
        nav_layout.setSpacing(10)

        self.prev_day_btn = QPushButton("← Previous Day")
        self.prev_day_btn.setObjectName("secondaryButton")
        self.prev_day_btn.clicked.connect(self.on_previous_day)

        self.today_btn = QPushButton("Today")
        self.today_btn.clicked.connect(self.on_today)

        self.next_day_btn = QPushButton("Next Day →")
        self.next_day_btn.setObjectName("secondaryButton")
        self.next_day_btn.clicked.connect(self.on_next_day)

        nav_layout.addWidget(self.prev_day_btn)
        nav_layout.addWidget(self.today_btn)
        nav_layout.addWidget(self.next_day_btn)

        left_layout.addLayout(nav_layout)

        # Middle panel - Activities list
        middle_panel = QWidget()
        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(10)

        # Activities header
        activities_header = QHBoxLayout()

        self.activities_label = QLabel("Activities for Today")
        self.activities_label.setObjectName("sectionTitle")
        activities_header.addWidget(self.activities_label)

        # Edit button
        self.edit_btn = QPushButton("Edit Activity")
        self.edit_btn.setObjectName("secondaryButton")
        self.edit_btn.clicked.connect(self.on_edit_activity)
        activities_header.addWidget(self.edit_btn)

        middle_layout.addLayout(activities_header)

        # Activities list
        self.activity_list = QListWidget()
        self.activity_list.setAlternatingRowColors(True)
        self.activity_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.activity_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        middle_layout.addWidget(self.activity_list)

        # Right panel - Daily Notes
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Notes header
        notes_header = QHBoxLayout()

        notes_label = QLabel("Daily Notes & Reflections")
        notes_label.setObjectName("sectionTitle")
        notes_header.addWidget(notes_label)

        # Save button
        self.save_notes_btn = QPushButton("Save Notes")
        self.save_notes_btn.setObjectName("successButton")
        self.save_notes_btn.clicked.connect(self.on_save_notes)
        notes_header.addWidget(self.save_notes_btn)

        right_layout.addLayout(notes_header)

        # Notes text editor
        self.notes_editor = QTextEdit()
        self.notes_editor.setPlaceholderText(
            "Write your thoughts, reflections, or notes about the day here..."
        )
        right_layout.addWidget(self.notes_editor)

        # Add panels to the content layout
        content_layout.addWidget(left_panel, 1)
        content_layout.addWidget(middle_panel, 2)
        content_layout.addWidget(right_panel, 2)

        # Add content frame to the daily layout
        daily_layout.addWidget(content_frame)

        # Add the daily tab to the tab widget
        self.tab_widget.addTab(daily_tab, "Daily View")

        # Load activities for the selected date
        self.load_activities_for_selected_date()

    def setup_summary_tab(self):
        """Set up the summary tab."""
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        summary_layout.setContentsMargins(0, 10, 0, 0)
        summary_layout.setSpacing(15)

        # Create a card-like container for the content
        content_frame = QFrame()
        content_frame.setObjectName("card")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)

        # Summary header
        header_layout = QHBoxLayout()

        summary_label = QLabel("View Summary for:")
        summary_label.setObjectName("sectionTitle")
        header_layout.addWidget(summary_label)

        # Date range selector
        self.summary_date_combo = QComboBox()
        self.summary_date_combo.addItems(
            ["Today", "Yesterday", "This Week", "Last Week", "This Month"]
        )
        self.summary_date_combo.currentIndexChanged.connect(
            self.on_summary_date_changed
        )
        header_layout.addWidget(self.summary_date_combo)

        header_layout.addStretch()
        content_layout.addLayout(header_layout)

        # Summary content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.summary_widget = DailySummaryWidget(self.db)
        scroll_area.setWidget(self.summary_widget)

        content_layout.addWidget(scroll_area)

        # Add content frame to the summary layout
        summary_layout.addWidget(content_frame)

        # Add the summary tab to the tab widget
        self.tab_widget.addTab(summary_tab, "Summary")

    def setup_analysis_tab(self):
        """Set up the analysis tab."""
        analysis_widget = AnalysisWidget(self.db)
        self.tab_widget.addTab(analysis_widget, "Analysis")

    def show_history(self):
        """Show the window with focus on the history view."""
        self.show()
        self.tab_widget.setCurrentIndex(0)  # Switch to daily view tab
        self.raise_()
        self.activateWindow()

    def refresh_data(self):
        """Refresh the activity data for the selected date."""
        self.load_activities_for_selected_date()
        if self.tab_widget.currentIndex() == 1:  # Summary tab
            self.on_summary_date_changed(self.summary_date_combo.currentIndex())

    def load_activities_for_selected_date(self):
        """Load activities for the currently selected date."""
        self.activity_list.clear()

        # Get the selected date
        qdate = self.calendar.selectedDate()
        date = datetime(qdate.year(), qdate.month(), qdate.day()).date()

        # Update the activities label
        if date == datetime.now().date():
            self.activities_label.setText("Activities for Today")
        else:
            date_str = date.strftime("%A, %B %d, %Y")
            self.activities_label.setText(f"Activities for {date_str}")

        # Get all hours for the day
        hours = []
        for hour in range(24):
            dt = datetime.combine(date, datetime.min.time().replace(hour=hour))
            hours.append(dt)

        # Get activities for the day
        day_start = datetime(date.year, date.month, date.day)
        activities = self.db.get_activities_for_day(day_start)

        # Create a dictionary for quick lookup
        activity_dict = {
            activity["hour"].hour: activity["activity"] for activity in activities
        }

        # Add items to the list
        for hour in hours:
            # Format the hour range (e.g., "9:00 AM - 10:00 AM")
            hour_range = format_hour_range(hour)

            # Get the activity for this hour
            activity_text = activity_dict.get(hour.hour, "[No activity recorded]")

            # Create a formatted item text
            item_text = f"{hour_range}: {activity_text}"

            # Create and add the item
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, hour)

            # Style based on whether there's an activity
            if hour.hour in activity_dict:
                item.setForeground(QColor("#2ecc71"))  # Green for recorded activities
                item.setData(Qt.ItemDataRole.UserRole + 1, "completed")
            else:
                # Red for missed hours in the past, normal for future hours
                now = datetime.now()
                if hour + timedelta(hours=1) < now and date <= now.date():
                    item.setForeground(QColor("#e74c3c"))  # Red for missed hours
                    item.setData(Qt.ItemDataRole.UserRole + 1, "missed")

            self.activity_list.addItem(item)

        # Load daily notes for the selected date
        daily_note = self.db.get_daily_note(day_start)
        self.notes_editor.setText(daily_note)

    @pyqtSlot()
    def on_date_selected(self):
        """Handle date selection in the calendar."""
        self.load_activities_for_selected_date()

    @pyqtSlot()
    def on_previous_day(self):
        """Navigate to the previous day."""
        current_date = self.calendar.selectedDate()
        prev_date = current_date.addDays(-1)
        self.calendar.setSelectedDate(prev_date)
        self.load_activities_for_selected_date()

    @pyqtSlot()
    def on_today(self):
        """Navigate to today."""
        self.calendar.setSelectedDate(QDate.currentDate())
        self.load_activities_for_selected_date()

    @pyqtSlot()
    def on_next_day(self):
        """Navigate to the next day."""
        current_date = self.calendar.selectedDate()
        next_date = current_date.addDays(1)
        self.calendar.setSelectedDate(next_date)
        self.load_activities_for_selected_date()

    @pyqtSlot()
    def on_edit_activity(self, item=None, hours=[], text=""):
        """Edit the selected activities."""
        if len(hours) == 0:
            selected_items = [item] if item else self.activity_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(
                    self, "No Selection", "Please select hours to edit."
                )
                return

            # Get all selected hours
            hours = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
            print(f"DEBUG: Selected hours: {hours}")

            text = (
                selected_items[0].text().split(":", 3)[3].strip()
            )  # Do the third one because it has two. The format is 11:00 AM - 12:00 PM: Activity.
            for item in selected_items[1:]:
                if item.text().split(":", 3)[3].strip() != text:
                    text = ""
                    break

        print(f"DEBUG: Extracted text: '{text}'")

        # Open dialog to enter activity for all selected hours
        dialog = ActivityInputDialog(parent=self, existing_text=text)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            activity_text = dialog.get_activity_text()
            print(f"DEBUG: New activity text: '{activity_text}'")

            if activity_text:
                # Record the activity for all selected hours
                print(f"DEBUG: About to record activity")
                self.scheduler.record_activity(hours, activity_text)
                print(f"DEBUG: Activity recorded")

                # Refresh the display
                self.refresh_data()
                print(f"DEBUG: Display refreshed")

    @pyqtSlot()
    def on_edit_current_activity(self):
        """Edit the activity for the current hour."""
        # get current datetime
        now = datetime.now()
        self.on_edit_activity(hours=[now])

    @pyqtSlot(QListWidgetItem)
    def on_item_double_clicked(self, item):
        """Handle double-clicking an activity item."""
        return self.on_edit_activity(item)

    @pyqtSlot(int)
    def on_tab_changed(self, index):
        """Handle changing tabs."""
        if index == 1:  # Summary tab
            self.on_summary_date_changed(self.summary_date_combo.currentIndex())

    @pyqtSlot(int)
    def on_summary_date_changed(self, index):
        """Handle changing the summary date selection."""
        today = datetime.now().date()

        if index == 0:  # Today
            self.summary_widget.set_date(today)
        elif index == 1:  # Yesterday
            yesterday = today - timedelta(days=1)
            self.summary_widget.set_date(yesterday)
        elif index == 2:  # This Week
            # This is simplified - just showing today for now
            self.summary_widget.set_date(today)
        elif index == 3:  # Last Week
            # This is simplified - just showing a week ago for now
            last_week = today - timedelta(days=7)
            self.summary_widget.set_date(last_week)
        elif index == 4:  # This Month
            # This is simplified - just showing today for now
            self.summary_widget.set_date(today)

    @pyqtSlot()
    def on_save_notes(self):
        """Save the daily notes."""
        notes = self.notes_editor.toPlainText()

        # Get the selected date
        qdate = self.calendar.selectedDate()
        date = datetime(qdate.year(), qdate.month(), qdate.day())

        # Save to database
        success = self.db.save_daily_note(date, notes)

        if success:
            QMessageBox.information(
                self,
                "Notes Saved",
                "Your daily notes have been saved successfully.",
                QMessageBox.StandardButton.Ok,
            )
        else:
            QMessageBox.warning(
                self,
                "Save Error",
                "There was an error saving your notes. Please try again.",
                QMessageBox.StandardButton.Ok,
            )

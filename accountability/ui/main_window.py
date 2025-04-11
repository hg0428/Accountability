"""
Main Window UI Module for Accountability App.
Provides the primary interface for viewing activity history.
"""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QCalendarWidget,
    QComboBox,
    QFrame,
    QAbstractItemView,
    QMessageBox,
    QGridLayout,
    QDialogButtonBox,
    QDialog,
    QScrollArea,
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
        self.setMinimumWidth(450)

        # Load stylesheet
        self.load_stylesheet()

        self.init_ui()

    def init_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Create a card-like container
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(20)

        # Title
        title = QLabel("Record Your Activity")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        # Hour display if provided
        if self.hour:
            hour_label = QLabel(f"Time: {format_hour_range(self.hour)}")
            hour_label.setObjectName("sectionTitle")
            hour_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(hour_label)

        # Activity input
        input_label = QLabel("What were you doing?")
        input_label.setObjectName("sectionTitle")
        card_layout.addWidget(input_label)

        self.activity_input = QTextEdit()
        self.activity_input.setPlaceholderText("Describe your activity here...")
        self.activity_input.setText(self.activity_text)
        self.activity_input.setMinimumHeight(120)
        card_layout.addWidget(self.activity_input)

        # Common activities (could be populated from frequently used activities)
        common_group = QGroupBox("Quick Select")
        common_layout = QGridLayout()
        common_layout.setSpacing(10)

        common_activities = [
            "Working",
            "Meeting",
            "Eating",
            "Break",
            "Exercise",
            "Reading",
            "Learning",
            "Sleeping",
            "Coding",
            "Writing",
            "Planning",
            "Relaxing",
        ]

        row, col = 0, 0
        for activity in common_activities:
            btn = QPushButton(activity)
            btn.setObjectName("secondaryButton")
            btn.clicked.connect(
                lambda checked, text=activity: self.activity_input.setText(text)
            )
            common_layout.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        common_group.setLayout(common_layout)
        card_layout.addWidget(common_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Style the buttons
        ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText("Save Activity")
        ok_button.setObjectName("successButton")

        cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setObjectName("secondaryButton")

        card_layout.addWidget(button_box)

        # Add the card to the main layout
        layout.addWidget(card)

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
        layout.setSpacing(12)

        # Date display
        date_container = QFrame()
        date_container.setObjectName("infoCard")
        date_layout = QHBoxLayout(date_container)
        date_layout.setContentsMargins(12, 12, 12, 12)

        self.date_label = QLabel()
        self.date_label.setObjectName("sectionTitle")
        date_layout.addWidget(self.date_label, 1)

        layout.addWidget(date_container)

        # Create scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Container for scrollable content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        # Activities summary section
        activities_frame = QFrame()
        activities_frame.setObjectName("card")
        activities_layout = QVBoxLayout(activities_frame)
        activities_layout.setContentsMargins(16, 16, 16, 16)
        activities_layout.setSpacing(10)

        activities_title = QLabel("Activity Summary")
        activities_title.setObjectName("sectionTitle")
        activities_layout.addWidget(activities_title)

        # Activity stats
        self.activity_stats = QLabel()
        self.activity_stats.setWordWrap(True)
        activities_layout.addWidget(self.activity_stats)

        # Activity list
        self.activity_list = QListWidget()
        self.activity_list.setAlternatingRowColors(True)
        self.activity_list.setMaximumHeight(300)
        activities_layout.addWidget(self.activity_list)

        content_layout.addWidget(activities_frame)

        # Productivity score section
        score_frame = QFrame()
        score_frame.setObjectName("card")
        score_layout = QVBoxLayout(score_frame)
        score_layout.setContentsMargins(16, 16, 16, 16)
        score_layout.setSpacing(10)

        score_title = QLabel("Productivity Score")
        score_title.setObjectName("sectionTitle")
        score_layout.addWidget(score_title)

        score_container = QHBoxLayout()

        self.score_label = QLabel()
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setStyleSheet(
            "font-size: 42px; font-weight: bold; color: #1a73e8;"
        )
        score_container.addWidget(self.score_label)

        score_layout.addLayout(score_container)

        self.score_description = QLabel()
        self.score_description.setWordWrap(True)
        score_layout.addWidget(self.score_description)

        content_layout.addWidget(score_frame)

        # Set the content widget to the scroll area
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Update the summary with current date
        self.update_summary()

    def set_date(self, date):
        """Set the date to display summary for."""
        self.date = date
        self.update_summary()

    def set_date_range(self, start_date, end_date):
        """Set the date range to display summary for."""
        self.date = start_date
        self.end_date = end_date
        self.update_summary()

    def update_summary(self):
        """Update the summary display with activities for the current date."""
        # Format and display the date
        if hasattr(self, "end_date"):
            date_str = f"{self.date.strftime('%A, %B %d, %Y')} - {self.end_date.strftime('%A, %B %d, %Y')}"
        else:
            date_str = self.date.strftime("%A, %B %d, %Y")
        self.date_label.setText(date_str)

        # Get activities for the date
        if hasattr(self, "end_date"):
            activities = self.db.get_activities_for_date_range(self.date, self.end_date)
        else:
            activities = self.db.get_activities_for_day(self.date)

        # Clear the activity list
        self.activity_list.clear()

        # Create a dictionary of activities by hour for quick lookup
        activity_dict = {}
        for activity in activities:
            hour = activity["hour"]
            activity_dict[hour.hour] = activity["activity"]

        # Count recorded hours
        recorded_hours = len(activities)
        # calculate total hours between start and end date or current date (whichever is sooner) (inclusive)
        if hasattr(self, "end_date"):
            if self.end_date <= datetime.now().date():
                end_date = datetime.now()
            else:
                end_date = datetime(
                    self.end_date.year, self.end_date.month, self.end_date.day
                ).replace(hour=23, minute=59, second=59, microsecond=999999)
            # start date is self.date with a time of 00:00:00
            start_date = datetime(self.date.year, self.date.month, self.date.day)
            total_possible_hours = (end_date - start_date).total_seconds() // 3600
        else:
            total_possible_hours = 24
        completion_rate = (recorded_hours / total_possible_hours) * 100

        # Display activity stats
        stats_text = f"Recorded {recorded_hours} out of {total_possible_hours} possible hours ({completion_rate:.1f}%)."
        self.activity_stats.setText(stats_text)

        # Calculate and display productivity score
        score = min(100, int(completion_rate * 1.2))  # Simple formula, capped at 100
        self.score_label.setText(f"{score}")

        # Set score color based on value
        if score >= 80:
            self.score_label.setStyleSheet(
                "font-size: 42px; font-weight: bold; color: #34a853;"
            )
            description = (
                "Excellent productivity! You've recorded most of your day's activities."
            )
        elif score >= 60:
            self.score_label.setStyleSheet(
                "font-size: 42px; font-weight: bold; color: #1a73e8;"
            )
            description = (
                "Good productivity. You're tracking most of your important activities."
            )
        elif score >= 40:
            self.score_label.setStyleSheet(
                "font-size: 42px; font-weight: bold; color: #fbbc04;"
            )
            description = (
                "Moderate productivity. Try to record more of your activities."
            )
        else:
            self.score_label.setStyleSheet(
                "font-size: 42px; font-weight: bold; color: #ea4335;"
            )
            description = "Low productivity tracking. Make an effort to record more of your daily activities."

        self.score_description.setText(description)

        # Add all hours to the list (0-23)
        for hour in range(24):
            # Create datetime for this hour
            hour_dt = datetime(self.date.year, self.date.month, self.date.day, hour)

            # Format the time range
            time_range = format_hour_range(hour_dt)

            # Check if there's an activity for this hour
            activity_text = activity_dict.get(hour, "No activity recorded")

            # Create list item
            item_text = f"{time_range}: {activity_text}"
            item = QListWidgetItem(item_text)

            # Style based on whether activity exists
            if hour not in activity_dict:
                item.setForeground(QColor("#9aa0a6"))  # Gray color for empty slots

            self.activity_list.addItem(item)


class MainWindow(QMainWindow):
    """Main window for the Accountability app."""

    def __init__(self, database, scheduler):
        """Initialize the main window."""
        super().__init__()

        self.db = database
        self.scheduler = scheduler

        self.init_ui()

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

    def init_ui(self):
        """Set up the user interface."""
        # Set window properties
        self.setWindowTitle("Accountability")
        self.setMinimumSize(900, 700)

        # Load stylesheet
        self.load_stylesheet()

        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Set up tabs
        self.setup_daily_tab()
        self.setup_summary_tab()
        self.setup_analysis_tab()

        # Add tabs to main layout
        main_layout.addWidget(self.tabs)

        # Set central widget
        self.setCentralWidget(central_widget)

    def setup_daily_tab(self):
        """Set up the daily view tab."""
        daily_tab = QWidget()
        daily_layout = QVBoxLayout(daily_tab)
        daily_layout.setContentsMargins(12, 12, 12, 12)
        daily_layout.setSpacing(12)

        # Header with date navigation
        header = QFrame()
        header.setObjectName("infoCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 12, 12, 12)

        # Previous day button
        prev_button = QPushButton("◀ Previous")
        prev_button.setObjectName("secondaryButton")
        prev_button.clicked.connect(self.on_previous_day)
        header_layout.addWidget(prev_button)

        # Today button
        today_button = QPushButton("Today")
        today_button.setObjectName("primaryButton")
        today_button.clicked.connect(self.on_today)
        header_layout.addWidget(today_button)

        # Next day button
        next_button = QPushButton("Next ▶")
        next_button.setObjectName("secondaryButton")
        next_button.clicked.connect(self.on_next_day)
        header_layout.addWidget(next_button)

        # Add header to layout
        daily_layout.addWidget(header)

        # Content area with calendar and activities
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        # Left side - Calendar
        calendar_container = QFrame()
        calendar_container.setObjectName("card")
        calendar_container.setMinimumWidth(320)  # Make calendar wider
        calendar_layout = QVBoxLayout(calendar_container)
        calendar_layout.setContentsMargins(12, 12, 12, 12)

        calendar_label = QLabel("Calendar")
        calendar_label.setObjectName("sectionTitle")
        calendar_layout.addWidget(calendar_label)

        self.calendar = QCalendarWidget()
        self.calendar.setMinimumWidth(300)  # Make calendar wider
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.on_date_selected)
        calendar_layout.addWidget(self.calendar)

        content_layout.addWidget(calendar_container, 3)

        # Right side - Activities and Notes
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Activities section
        activities_frame = QFrame()
        activities_frame.setObjectName("card")
        activities_layout = QVBoxLayout(activities_frame)
        activities_layout.setContentsMargins(12, 12, 12, 12)

        # Activities header with title and edit button
        activities_header = QHBoxLayout()
        activities_label = QLabel("Activities")
        activities_label.setObjectName("sectionTitle")
        activities_header.addWidget(activities_label)

        # Add current hour button
        current_hour_btn = QPushButton("Record Current Hour")
        current_hour_btn.setObjectName("primaryButton")
        current_hour_btn.clicked.connect(self.on_edit_current_activity)
        activities_header.addWidget(current_hour_btn)

        edit_button = QPushButton("Edit Selected")
        edit_button.setObjectName("secondaryButton")
        edit_button.clicked.connect(self.on_edit_activity)
        activities_header.addWidget(edit_button)

        activities_layout.addLayout(activities_header)

        # Activities list
        self.activity_list = QListWidget()
        self.activity_list.setAlternatingRowColors(True)
        self.activity_list.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection
        )
        self.activity_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.activity_list.setMinimumHeight(300)  # Set minimum height
        activities_layout.addWidget(self.activity_list)

        right_layout.addWidget(activities_frame)

        # Notes section
        notes_frame = QFrame()
        notes_frame.setObjectName("card")
        notes_layout = QVBoxLayout(notes_frame)
        notes_layout.setContentsMargins(12, 12, 12, 12)

        # Notes header with title and save button
        notes_header = QHBoxLayout()
        notes_label = QLabel("Daily Notes")
        notes_label.setObjectName("sectionTitle")
        notes_header.addWidget(notes_label)

        save_button = QPushButton("Save Notes")
        save_button.setObjectName("successButton")
        save_button.clicked.connect(self.on_save_notes)
        notes_header.addWidget(save_button)

        notes_layout.addLayout(notes_header)

        # Notes editor
        self.notes_editor = QTextEdit()
        self.notes_editor.setPlaceholderText("Add your notes for the day here...")
        self.notes_editor.setMinimumHeight(150)  # Set minimum height
        notes_layout.addWidget(self.notes_editor)

        right_layout.addWidget(notes_frame)

        content_layout.addWidget(right_container, 7)

        daily_layout.addWidget(content)

        self.tabs.addTab(daily_tab, "Daily View")

    def setup_summary_tab(self):
        """Set up the summary tab."""
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        summary_layout.setContentsMargins(16, 24, 16, 16)
        summary_layout.setSpacing(24)

        # Create header
        header_frame = QFrame()
        header_frame.setObjectName("card")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 20, 24, 20)
        header_layout.setSpacing(16)

        # Summary title
        summary_title = QLabel("Activity Summary")
        summary_title.setObjectName("appTitle")
        summary_title.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Date range selector
        selector_container = QWidget()
        selector_layout = QHBoxLayout(selector_container)
        selector_layout.setContentsMargins(0, 0, 0, 0)
        selector_layout.setSpacing(12)

        date_label = QLabel("Time Period:")
        date_label.setObjectName("sectionTitle")
        selector_layout.addWidget(date_label)

        self.summary_date_combo = QComboBox()
        self.summary_date_combo.addItems(
            [
                "Today",
                "Yesterday",
                "This Week",
                "Last Week",
                "This Month",
                "Custom Range",
            ]
        )
        self.summary_date_combo.currentIndexChanged.connect(
            self.on_summary_date_changed
        )
        self.summary_date_combo.setMinimumWidth(180)
        selector_layout.addWidget(self.summary_date_combo)

        # Date range picker (initially hidden)
        self.summary_date_range_container = QWidget()
        date_range_layout = QHBoxLayout(self.summary_date_range_container)
        date_range_layout.setContentsMargins(0, 0, 0, 0)
        date_range_layout.setSpacing(8)

        from_label = QLabel("From:")
        date_range_layout.addWidget(from_label)

        self.summary_start_date = QCalendarWidget()
        self.summary_start_date.setGridVisible(True)
        self.summary_start_date.setMaximumWidth(300)
        self.summary_start_date.setMaximumHeight(250)
        date_range_layout.addWidget(self.summary_start_date)

        to_label = QLabel("To:")
        date_range_layout.addWidget(to_label)

        self.summary_end_date = QCalendarWidget()
        self.summary_end_date.setGridVisible(True)
        self.summary_end_date.setMaximumWidth(300)
        self.summary_end_date.setMaximumHeight(250)
        date_range_layout.addWidget(self.summary_end_date)

        apply_button = QPushButton("Apply Range")
        apply_button.setObjectName("primaryButton")
        apply_button.clicked.connect(self.on_apply_summary_date_range)
        date_range_layout.addWidget(apply_button)

        self.summary_date_range_container.setVisible(False)

        # Add widgets to header layout
        header_layout.addWidget(summary_title, 1)
        header_layout.addWidget(selector_container)

        summary_layout.addWidget(header_frame)
        summary_layout.addWidget(self.summary_date_range_container)

        # Summary content
        content_frame = QFrame()
        content_frame.setObjectName("card")
        content_layout = QVBoxLayout(content_frame)

        # Create summary widget
        self.summary_widget = DailySummaryWidget(self.db)
        content_layout.addWidget(self.summary_widget)

        summary_layout.addWidget(content_frame)

        # Add tab
        self.tabs.addTab(summary_tab, "Summary")

    def setup_analysis_tab(self):
        """Set up the analysis tab."""
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        analysis_layout.setContentsMargins(16, 24, 16, 16)
        analysis_layout.setSpacing(24)

        # Analysis content
        content_frame = QFrame()
        content_frame.setObjectName("card")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        # Create analysis widget
        self.analysis_widget = AnalysisWidget(self.db)
        content_layout.addWidget(self.analysis_widget)

        analysis_layout.addWidget(content_frame)

        # Add tab
        self.tabs.addTab(analysis_tab, "Analysis")

    def show_history(self):
        """Show the window with focus on the history view."""
        self.show()
        self.tabs.setCurrentIndex(0)  # Switch to daily view tab
        self.raise_()
        self.activateWindow()

    def refresh_data(self):
        """Refresh the activity data for the selected date."""
        self.load_activities_for_selected_date()
        if self.tabs.currentIndex() == 1:  # Summary tab
            self.on_summary_date_changed(self.summary_date_combo.currentIndex())

    def load_activities_for_selected_date(self):
        """Load activities for the currently selected date."""
        # Clear the activity list
        self.activity_list.clear()

        # Get the selected date
        qdate = self.calendar.selectedDate()
        date = datetime(qdate.year(), qdate.month(), qdate.day())

        # Format the date for display
        formatted_date = date.strftime("%A, %B %d, %Y")
        self.setWindowTitle(f"Accountability - {formatted_date}")

        # Get activities for the selected date
        activities = self.db.get_activities_for_day(date)

        # Create a dictionary of activities by hour for quick lookup
        activity_dict = {}
        for activity in activities:
            hour = activity["hour"]
            activity_dict[hour.hour] = activity["activity"]

        # Add all hours to the list (0-23)
        for hour in range(24):
            # Create datetime for this hour
            hour_dt = datetime(date.year, date.month, date.day, hour)

            # Format the time range
            time_range = format_hour_range(hour_dt)

            # Check if there's an activity for this hour
            if hour in activity_dict:
                activity_text = activity_dict[hour]
                item_text = f"{time_range}: {activity_text}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, hour_dt)

                # Style for completed hours
                item.setForeground(QColor("#202124"))  # Dark text
                item.setData(Qt.ItemDataRole.UserRole + 1, "completed")
            else:
                # Hour without activity
                item_text = f"{time_range}: No activity recorded"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, hour_dt)
                item.setForeground(QColor("#9aa0a6"))  # Gray text
                item.setData(Qt.ItemDataRole.UserRole + 1, "empty")

            self.activity_list.addItem(item)

        # Load notes for the selected date
        notes = self.db.get_daily_note(date)
        self.notes_editor.setText(notes if notes else "")

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

        # Hide date range picker by default
        self.summary_date_range_container.setVisible(False)

        if index == 0:  # Today
            self.summary_widget.set_date(today)
        elif index == 1:  # Yesterday
            yesterday = today - timedelta(days=1)
            self.summary_widget.set_date(yesterday)
        elif index == 2:  # This Week
            # Start of current week (Monday)
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            self.summary_widget.set_date_range(start_of_week, end_of_week)
        elif index == 3:  # Last Week
            # Start of last week
            start_of_last_week = today - timedelta(days=today.weekday() + 7)
            end_of_last_week = start_of_last_week + timedelta(days=6)
            self.summary_widget.set_date_range(start_of_last_week, end_of_last_week)
        elif index == 4:  # This Month
            # Start of current month
            start_of_month = today.replace(day=1)
            # Calculate end of month
            if today.month == 12:
                end_of_month = today.replace(
                    year=today.year + 1, month=1, day=1
                ) - timedelta(days=1)
            else:
                end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(
                    days=1
                )
            self.summary_widget.set_date_range(start_of_month, end_of_month)
        elif index == 5:  # Custom Range
            # Show date range picker
            self.summary_date_range_container.setVisible(True)
            # Set default range (last 7 days)
            self.summary_start_date.setSelectedDate(
                QDate.fromString(
                    (today - timedelta(days=7)).strftime("%Y-%m-%d"), "yyyy-MM-dd"
                )
            )
            self.summary_end_date.setSelectedDate(
                QDate.fromString(today.strftime("%Y-%m-%d"), "yyyy-MM-dd")
            )

    def on_apply_summary_date_range(self):
        """Apply the custom date range for summary."""
        start_date = self.summary_start_date.selectedDate()
        end_date = self.summary_end_date.selectedDate()

        # Convert QDate to Python date
        start_date_py = datetime(
            start_date.year(), start_date.month(), start_date.day()
        ).date()
        end_date_py = datetime(end_date.year(), end_date.month(), end_date.day()).date()

        # Ensure start date is before or equal to end date
        if start_date_py > end_date_py:
            QMessageBox.warning(
                self,
                "Invalid Date Range",
                "Start date must be before or equal to end date.",
                QMessageBox.StandardButton.Ok,
            )
            return

        # Update summary with date range
        self.summary_widget.set_date_range(start_date_py, end_date_py)

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

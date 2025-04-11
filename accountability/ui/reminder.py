"""
Reminder Dialog UI Module for Accountability App.
Provides the popup reminder for recording hourly activities.
"""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QDialogButtonBox,
    QFrame,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QIcon


class ReminderDialog(QDialog):
    """Dialog that pops up to remind the user to record activities."""

    def __init__(self, hours, database, scheduler, parent=None):
        """
        Initialize the reminder dialog.

        Args:
            hours: List of datetime objects representing hours to record
            database: Database instance
            scheduler: ActivityScheduler instance
            parent: Parent widget
        """
        super().__init__(parent)

        self.hours = hours
        self.db = database
        self.scheduler = scheduler
        self.selected_hours = []

        # Configure dialog
        self.setWindowTitle("Record Your Activities")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(550, 450)

        # Load stylesheet
        self.load_stylesheet()

        # Build UI
        self.init_ui()

        # Don't allow closing with X button
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Create a card-like container
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        # Title and explanation
        title = QLabel("What were you doing?")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        # Count of hours to fill in
        hours_count = len(self.hours)
        if hours_count == 1:
            subtitle = QLabel(f"Please record your activity for the past hour:")
        else:
            subtitle = QLabel(f"Please record your activities for {hours_count} hours:")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)

        # List of hours
        hours_container = QFrame()
        hours_container.setObjectName("infoCard")
        hours_layout = QVBoxLayout(hours_container)
        hours_layout.setContentsMargins(12, 12, 12, 12)
        hours_layout.setSpacing(8)
        
        hours_label = QLabel("Select hours:")
        hours_label.setObjectName("sectionTitle")
        hours_layout.addWidget(hours_label)

        self.hour_list = QListWidget()
        self.hour_list.setAlternatingRowColors(True)
        self.hour_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.hour_list.setMaximumHeight(180)
        self.populate_hour_list()
        hours_layout.addWidget(self.hour_list)

        # Info label
        info_label = QLabel(
            "You can select multiple hours and enter the same activity for all of them."
        )
        info_label.setObjectName("subtitle")
        info_label.setStyleSheet("font-style: italic; color: #5f6368;")
        hours_layout.addWidget(info_label)
        
        card_layout.addWidget(hours_container)

        # Activity input
        input_label = QLabel("Activity Description:")
        input_label.setObjectName("sectionTitle")
        card_layout.addWidget(input_label)

        self.activity_input = QTextEdit()
        self.activity_input.setPlaceholderText("What were you doing during this time?")
        self.activity_input.setMinimumHeight(120)
        card_layout.addWidget(self.activity_input)

        # Quick suggestions
        suggestions_container = QFrame()
        suggestions_layout = QHBoxLayout(suggestions_container)
        suggestions_layout.setContentsMargins(0, 0, 0, 0)
        suggestions_layout.setSpacing(8)
        
        suggestions = ["Working", "Meeting", "Break", "Learning"]
        for suggestion in suggestions:
            btn = QPushButton(suggestion)
            btn.setObjectName("secondaryButton")
            btn.clicked.connect(lambda checked, text=suggestion: self.activity_input.setText(text))
            suggestions_layout.addWidget(btn)
            
        card_layout.addLayout(suggestions_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.snooze_button = QPushButton("Snooze (10 min)")
        self.snooze_button.setObjectName("secondaryButton")
        self.snooze_button.setIcon(QIcon.fromTheme("appointment-soon"))
        self.snooze_button.clicked.connect(self.on_snooze)

        self.record_button = QPushButton("Record Activity")
        self.record_button.setObjectName("successButton")
        self.record_button.setDefault(True)
        self.record_button.clicked.connect(self.on_record)

        button_layout.addWidget(self.snooze_button)
        button_layout.addWidget(self.record_button)

        card_layout.addLayout(button_layout)

        # Add the card to the main layout
        layout.addWidget(card)

    def populate_hour_list(self):
        """Populate the list with hours that need to be recorded."""
        self.hour_list.clear()

        for hour in sorted(self.hours):
            # Format the hour range (e.g., "9:00 AM - 10:00 AM")
            start_time = hour.strftime("%I:%M %p").lstrip("0")
            end_time = (hour + timedelta(hours=1)).strftime("%I:%M %p").lstrip("0")
            item_text = f"{start_time} - {end_time}"

            # Create and add the item
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, hour)

            # Style the item
            now = datetime.now()
            if hour + timedelta(hours=1) < now:
                # Past hours (missed)
                item.setForeground(QColor("#ea4335"))  # Red for missed hours
                item.setData(Qt.ItemDataRole.UserRole + 1, "missed")
                item.setText(f"⚠️ {item_text} (missed)")
            else:
                item.setText(f"🕒 {item_text}")

            self.hour_list.addItem(item)

        # Select the first hour by default
        if self.hour_list.count() > 0:
            self.hour_list.item(0).setSelected(True)

    @pyqtSlot()
    def on_record(self):
        """Record the activity for selected hours."""
        selected_items = self.hour_list.selectedItems()
        if not selected_items:
            return

        activity_text = self.activity_input.toPlainText().strip()
        if not activity_text:
            return

        # Get the selected hours
        selected_hours = [
            item.data(Qt.ItemDataRole.UserRole) for item in selected_items
        ]

        # Record the activity for each selected hour
        self.scheduler.record_activity(selected_hours, activity_text)

        # Remove recorded hours from the list
        for item in selected_items:
            hour = item.data(Qt.ItemDataRole.UserRole)
            if hour in self.hours:
                self.hours.remove(hour)

        # Clear the input field
        self.activity_input.clear()

        # Repopulate the list
        self.populate_hour_list()

        # If all hours have been recorded, close the dialog
        if not self.hours:
            self.accept()

    @pyqtSlot()
    def on_snooze(self):
        """Snooze the reminder for 10 minutes."""
        self.reject()  # Will be shown again by the scheduler's timer

    def closeEvent(self, event):
        """Override close event to prevent closing with X button."""
        # Only allow closing if there are no hours left to record
        if not self.hours:
            event.accept()
        else:
            event.ignore()

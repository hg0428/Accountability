"""
Analysis Widget for Accountability App.
Provides AI-powered analysis of user activities and patterns.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QSpacerItem,
    QProgressBar,
    QStackedWidget,
    QMessageBox,
    QFileDialog,
    QCalendarWidget,
    QGraphicsView,
    QGraphicsScene,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QDate, QRectF, QPointF
from PyQt6.QtGui import QFont, QIcon, QPainterPath, QPainter, QBrush, QPen, QColor
from math import pi, cos, sin

from ..ai_analysis import AIAnalyzer
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

class AnalysisWorker(QThread):
    """Worker thread for running AI analysis without blocking the UI."""

    analysis_complete = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)

    def __init__(
        self, analyzer, activities, date_range, force_reload=False, notes_dict=None
    ):
        """Initialize the worker thread."""
        super().__init__()
        self.analyzer = analyzer
        self.activities = activities
        self.date_range = date_range
        self.force_reload = force_reload
        self.notes_dict = notes_dict

    def run(self):
        """Run the analysis in a separate thread."""
        try:
            # If force_reload is True, we'll clear any cached analysis first
            if (
                self.force_reload
                and hasattr(self.analyzer, "db_path")
                and self.analyzer.db_path
            ):
                import sqlite3

                conn = sqlite3.connect(self.analyzer.db_path)
                cursor = conn.cursor()

                # Calculate date range
                start_date, end_date = self.analyzer._get_date_range_bounds(
                    self.date_range, self.activities
                )
                if start_date and end_date:
                    # Delete any existing analysis for this date range
                    cursor.execute(
                        """
                    DELETE FROM analysis_results 
                    WHERE date_range = ? AND start_date = ? AND end_date = ?
                    """,
                        (self.date_range, start_date.isoformat(), end_date.isoformat()),
                    )
                    conn.commit()
                    print(
                        f"Deleted cached analysis for {self.date_range} ({start_date.isoformat()} to {end_date.isoformat()})"
                    )
                conn.close()

            # Run the analysis
            print(
                f"Starting analysis for {self.date_range} with {len(self.activities)} activities"
            )
            result = self.analyzer.analyze_activities(
                self.activities, self.date_range, notes_dict=self.notes_dict
            )
            print(f"Analysis complete for {self.date_range}")
            self.analysis_complete.emit(result)
        except Exception as e:
            print(f"Error in analysis worker: {str(e)}")
            self.analysis_error.emit(str(e))


class AnalysisWidget(QWidget):
    """Widget for displaying AI analysis of user activities."""

    def __init__(self, database, analyzer, parent=None):
        """Initialize the analysis widget."""
        super().__init__(parent)
        self.activities_db = database
        self.analyzer = analyzer
        self.analysis_in_progress = False
        self.current_date_range = "Today"
        self.setup_ui()

    def setup_ui(self):
        """Set up the UI elements."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Top controls
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(16, 16, 16, 0)

        # Date range selector
        date_range_label = QLabel("Date Range:")
        self.date_range_combo = QComboBox()
        self.date_range_combo.addItems(
            [
                "Today",
                "Yesterday",
                "This Week",
                "Last Week",
                "This Month",
                "Last Month",
                "Custom Range",
            ]
        )
        self.date_range_combo.currentIndexChanged.connect(self.on_date_range_changed)

        # Custom date range controls (initially hidden)
        self.date_range_frame = QFrame()
        self.date_range_frame.setVisible(False)
        date_range_frame_layout = QVBoxLayout(self.date_range_frame)
        date_range_frame_layout.setContentsMargins(0, 8, 0, 8)

        # Start and end date selectors
        date_selectors_layout = QHBoxLayout()

        start_date_layout = QVBoxLayout()
        start_date_label = QLabel("Start Date:")
        self.start_date_calendar = QCalendarWidget()
        self.start_date_calendar.setGridVisible(True)
        self.start_date_calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        start_date_layout.addWidget(start_date_label)
        start_date_layout.addWidget(self.start_date_calendar)

        end_date_layout = QVBoxLayout()
        end_date_label = QLabel("End Date:")
        self.end_date_calendar = QCalendarWidget()
        self.end_date_calendar.setGridVisible(True)
        self.end_date_calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        end_date_layout.addWidget(end_date_label)
        end_date_layout.addWidget(self.end_date_calendar)

        date_selectors_layout.addLayout(start_date_layout)
        date_selectors_layout.addLayout(end_date_layout)
        date_range_frame_layout.addLayout(date_selectors_layout)

        # Apply custom date range button
        apply_button_layout = QHBoxLayout()
        apply_button_layout.addStretch()
        self.apply_date_range_button = QPushButton("Apply Date Range")
        self.apply_date_range_button.clicked.connect(self.on_apply_date_range)
        apply_button_layout.addWidget(self.apply_date_range_button)
        date_range_frame_layout.addLayout(apply_button_layout)

        # Add refresh button and spacing
        self.refresh_button = QPushButton("Refresh Analysis")
        self.refresh_button.clicked.connect(lambda: self.update_analysis(force_reload=True))

        # Add loading indicator
        self.loading_label = QLabel("Analysis in progress...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet(
            "color: #4285f4; font-weight: bold; font-size: 14px;"
        )
        self.loading_label.setVisible(False)

        # Add controls to layout
        controls_layout.addWidget(date_range_label)
        controls_layout.addWidget(self.date_range_combo)
        controls_layout.addStretch()
        controls_layout.addWidget(self.refresh_button)

        # Add controls to main layout
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.date_range_frame)
        main_layout.addWidget(self.loading_label)

        # Create stacked widget for content
        self.content_stack = QStackedWidget()

        # Create placeholder for when no analysis is available
        self.placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_text = QLabel("Select a date range to analyze your activities.")
        placeholder_text.setObjectName("placeholderText")
        placeholder_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(placeholder_text)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create scroll area for analysis results
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Create container for analysis results
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(20)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.scroll_area.setWidget(self.content_widget)

        # Add widgets to stacked widget
        self.content_stack.addWidget(self.placeholder_widget)
        self.content_stack.addWidget(self.scroll_area)
        self.content_stack.setCurrentWidget(self.placeholder_widget)

        # Add stacked widget to main layout
        main_layout.addWidget(self.content_stack)

        # Initialize with current date
        self.start_date_calendar.setSelectedDate(QDate.currentDate().addDays(-7))
        self.end_date_calendar.setSelectedDate(QDate.currentDate())

        # Update analysis
        self.update_analysis()

    def on_date_range_changed(self, index):
        """Handle date range selection change."""
        # Hide date range picker by default
        self.date_range_frame.setVisible(False)

        # If custom range is selected, show the date picker
        if index == 6:  # Custom Range
            self.date_range_frame.setVisible(True)
            # No need to start analysis yet, wait for user to apply the range
        else:
            # For predefined ranges, start analysis immediately
            self.update_analysis()

    def on_apply_date_range(self):
        """Apply the custom date range and start analysis."""
        # Start analysis with the selected date range
        self.update_analysis()

    def update_analysis(self, force_reload=False):
        """Start the AI analysis process."""
        # Show loading indicator
        self.loading_label.setVisible(True)
        self.refresh_button.setEnabled(False)

        # Get selected date range
        period_text = self.date_range_combo.currentText()

        # Calculate date range
        end_date = datetime.now()
        start_date = None

        if period_text == "Today":
            start_date = datetime(end_date.year, end_date.month, end_date.day)
        elif period_text == "Yesterday":
            yesterday = end_date - timedelta(days=1)
            start_date = datetime(yesterday.year, yesterday.month, yesterday.day)
            end_date = datetime(
                yesterday.year, yesterday.month, yesterday.day, 23, 59, 59
            )
        elif period_text == "This Week":
            # Start of current week (Monday)
            start_date = end_date - timedelta(days=end_date.weekday())
            start_date = datetime(start_date.year, start_date.month, start_date.day)
        elif period_text == "Last Week":
            # Start of last week (Monday)
            start_of_last_week = end_date - timedelta(days=end_date.weekday() + 7)
            start_date = datetime(
                start_of_last_week.year, start_of_last_week.month, start_of_last_week.day
            )
            end_of_last_week = start_of_last_week + timedelta(days=6)
            end_date = datetime(
                end_of_last_week.year, end_of_last_week.month, end_of_last_week.day, 23, 59, 59
            )
        elif period_text == "This Month":
            # Start of current month
            start_date = datetime(end_date.year, end_date.month, 1)
        elif period_text == "Last Month":
            # Start of last month
            if end_date.month == 1:
                start_date = datetime(end_date.year - 1, 12, 1)
                end_date = datetime(end_date.year, 1, 1) - timedelta(seconds=1)
            else:
                start_date = datetime(end_date.year, end_date.month - 1, 1)
                end_date = datetime(end_date.year, end_date.month, 1) - timedelta(seconds=1)
        elif period_text == "Custom Range":
            # Get dates from calendar widgets
            start_qdate = self.start_date_calendar.selectedDate()
            end_qdate = self.end_date_calendar.selectedDate()

            # Convert to Python datetime
            start_date = datetime(start_qdate.year(), start_qdate.month(), start_qdate.day())
            end_date = datetime(end_qdate.year(), end_qdate.month(), end_qdate.day(), 23, 59, 59)

            # Validate date range
            if start_date > end_date:
                self.handle_analysis_error("Start date must be before or equal to end date.")
                return
        else:
            start_date = end_date - timedelta(days=1)

        # Get activities for the date range
        activities = []
        current_date = start_date

        while current_date <= end_date:
            day_start = datetime(
                current_date.year, current_date.month, current_date.day
            )
            day_activities = self.activities_db.get_activities_for_day(day_start)
            activities.extend(day_activities)
            current_date += timedelta(days=1)

        # Get daily notes for the date range
        notes_dict = {}
        if hasattr(self.activities_db, "get_notes_for_date_range"):
            try:
                notes_dict = self.activities_db.get_notes_for_date_range(start_date, end_date)
                print(f"Retrieved {len(notes_dict)} daily notes for analysis")
            except Exception as e:
                print(f"Error retrieving daily notes: {e}")

        # Set API type based on selection
        api_type = (
            "ollama" if self.analyzer.api_type == "ollama" else "openai"
        )

        # Store current date range
        self.current_date_range = period_text

        # Create and start worker thread
        self.worker = AnalysisWorker(
            self.analyzer, activities, period_text, force_reload, notes_dict
        )
        self.worker.analysis_complete.connect(self.update_analysis_results)
        self.worker.analysis_error.connect(self.handle_analysis_error)
        self.worker.finished.connect(lambda: self.refresh_button.setEnabled(True))
        self.worker.finished.connect(lambda: self.loading_label.setVisible(False))
        self.worker.start()

    def update_analysis_results(self, results):
        """Update the UI with analysis results."""
        # Hide loading indicator
        self.loading_label.setVisible(False)
        self.refresh_button.setEnabled(True)

        # Store current analysis
        self.current_analysis = results

        # Hide placeholder and show results container
        self.content_stack.setCurrentWidget(self.scroll_area)

        # Clear previous results
        self.clear_results_container()

        # Create a top row with productivity score and summary
        self.create_top_row(results)

        # Create a row with patterns and insights
        self.create_middle_row(results)

        # Create a row with recommendations
        self.create_recommendations_row(results)

    def clear_results_container(self):
        """Clear all widgets from the results container."""
        # Remove all widgets from the results layout
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def create_card(self, title, content_widget):
        """Create a card with a title and content widget."""
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        # Add title
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        card_layout.addWidget(title_label)

        # Add content
        card_layout.addWidget(content_widget)

        return card

    def create_top_row(self, results):
        """Create the top row with productivity score and summary."""
        # Create a horizontal layout for the top row
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(20)

        # Create productivity score widget (left side)
        if "productivity_score" in results:
            try:
                score = float(results["productivity_score"])
                score_widget = self.create_productivity_score_widget(score, results.get("productivity_explanation", ""))
                top_layout.addWidget(score_widget, 1)  # 1:2 ratio
            except (ValueError, TypeError):
                # Skip if score is not a valid number
                pass

        # Create summary widget (right side)
        if "summary" in results and results["summary"]:
            summary_text = QTextEdit()
            summary_text.setReadOnly(True)
            summary_text.setMinimumHeight(180)

            # Format the summary text with HTML
            try:
                summary_text.setHtml(results["summary"])
            except (ValueError, TypeError):
                summary_text.setPlainText(results["summary"])

            summary_card = self.create_card("Activity Summary", summary_text)
            top_layout.addWidget(summary_card, 2)  # 1:2 ratio

        # Add the top row to the results layout
        self.content_layout.addWidget(top_row)

    def create_middle_row(self, results):
        """Create the middle row with patterns and insights."""
        # Create a horizontal layout for the middle row
        middle_row = QWidget()
        middle_layout = QHBoxLayout(middle_row)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(20)

        # Create patterns widget (left side)
        if "patterns" in results and results["patterns"]:
            patterns_text = QTextEdit()
            patterns_text.setReadOnly(True)
            patterns_text.setMinimumHeight(150)

            # Format the patterns as a bulleted list
            patterns_html = "<ul>"
            for pattern in results["patterns"]:
                patterns_html += f"<li>{pattern}</li>"
            patterns_html += "</ul"

            patterns_text.setHtml(patterns_html)
            patterns_card = self.create_card("Activity Patterns", patterns_text)
            middle_layout.addWidget(patterns_card)

        # Create insights widget (right side)
        if "insights" in results and results["insights"]:
            insights_text = QTextEdit()
            insights_text.setReadOnly(True)
            insights_text.setMinimumHeight(150)

            # Format the insights as a bulleted list
            insights_html = "<ul>"
            for insight in results["insights"]:
                insights_html += f"<li>{insight}</li>"
            insights_html += "</ul"

            insights_text.setHtml(insights_html)
            insights_card = self.create_card("Key Insights", insights_text)
            middle_layout.addWidget(insights_card)

        # Add the middle row to the results layout
        self.content_layout.addWidget(middle_row)

    def create_recommendations_row(self, results):
        """Create the recommendations row."""
        if "recommendations" not in results or not results["recommendations"]:
            return

        recommendations_text = QTextEdit()
        recommendations_text.setReadOnly(True)
        recommendations_text.setMinimumHeight(150)

        # Format the recommendations as a bulleted list
        recommendations_html = "<ul>"
        for recommendation in results["recommendations"]:
            recommendations_html += f"<li>{recommendation}</li>"
        recommendations_html += "</ul"

        recommendations_text.setHtml(recommendations_html)
        recommendations_card = self.create_card("Recommendations", recommendations_text)

        # Add the recommendations card to the results layout
        self.content_layout.addWidget(recommendations_card)

    def create_productivity_score_widget(self, score, explanation):
        """Create a circular productivity score widget."""
        # Create a frame for the productivity score
        score_frame = QFrame()
        score_frame.setObjectName("card")
        score_layout = QVBoxLayout(score_frame)
        score_layout.setContentsMargins(16, 16, 16, 16)
        score_layout.setSpacing(12)

        # Add title
        title_label = QLabel("Productivity Score")
        title_label.setObjectName("sectionTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_layout.addWidget(title_label)

        # Create circular progress indicator
        class CircularProgressIndicator(QGraphicsView):
            def __init__(self, score, parent=None):
                super().__init__(parent)
                self.score = min(max(float(score), 0), 10)  # Clamp between 0 and 10
                self.setMinimumSize(180, 180)
                self.setMaximumSize(180, 180)
                self.setRenderHint(QPainter.RenderHint.Antialiasing)
                self.setFrameShape(QFrame.Shape.NoFrame)
                self.setBackgroundBrush(QBrush(QColor("#ffffff")))

                # Create scene
                self.scene = QGraphicsScene(self)
                self.setScene(self.scene)

                # Draw the progress indicator
                self.draw_progress()

            def draw_progress(self):
                self.scene.clear()

                # Calculate percentage
                percentage = self.score / 10.0

                # Define colors based on score
                if self.score >= 8:
                    color = QColor("#34a853")  # Green for high scores
                elif self.score >= 6:
                    color = QColor("#4285f4")  # Blue for medium-high scores
                elif self.score >= 4:
                    color = QColor("#fbbc04")  # Yellow for medium scores
                else:
                    color = QColor("#ea4335")  # Red for low scores

                # Draw background circle
                background_pen = QPen(QColor("#e0e0e0"), 10)
                background_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                self.scene.addEllipse(20, 20, 140, 140, background_pen, QBrush(Qt.BrushStyle.NoBrush))

                # Draw progress arc using path
                progress_pen = QPen(color, 10)
                progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

                if percentage > 0:  # Only draw arc if score is greater than 0
                    # Calculate start and span angles (in degrees)
                    start_angle = 90  # Start at top (90 degrees)
                    span_angle = percentage * 360  # Clockwise

                    # Create arc path
                    path = QPainterPath()

                    # Draw the arc
                    rect = QRectF(20, 20, 140, 140)

                    # Start at the top of the circle
                    path.moveTo(90, 20)

                    # Draw the arc clockwise
                    path.arcTo(rect, start_angle, -span_angle)

                    self.scene.addPath(path, progress_pen)

                # Add score text
                score_text = self.scene.addText(f"{self.score:.1f}", QFont("Arial", 24, QFont.Weight.Bold))
                score_text.setDefaultTextColor(color)

                # Center the text
                text_rect = score_text.boundingRect()
                score_text.setPos(90 - text_rect.width() / 2, 70 - text_rect.height() / 2)

                # Add "out of 10" text
                out_of_text = self.scene.addText("out of 10", QFont("Arial", 10))
                out_of_text.setDefaultTextColor(QColor("#5f6368"))

                # Center the "out of 10" text
                out_rect = out_of_text.boundingRect()
                out_of_text.setPos(90 - out_rect.width() / 2, 100 - out_rect.height() / 2)

        # Create the circular progress indicator with a default score if none is provided
        try:
            score_value = float(score) if score is not None else 0.0
        except (ValueError, TypeError):
            score_value = 0.0

        circular_progress = CircularProgressIndicator(score_value)
        score_layout.addWidget(circular_progress, alignment=Qt.AlignmentFlag.AlignCenter)

        # Add explanation if available
        if explanation:
            explanation_label = QLabel(explanation)
            explanation_label.setWordWrap(True)
            explanation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            explanation_label.setObjectName("explanationText")
            score_layout.addWidget(explanation_label)

        return score_frame

    def handle_analysis_error(self, error_message):
        """Handle errors during analysis."""
        # Hide loading indicator
        self.loading_label.setVisible(False)
        self.refresh_button.setEnabled(True)

        # Show error message
        QMessageBox.critical(
            self,
            "Analysis Error",
            f"An error occurred during analysis: {error_message}\n\n"
            f"If using Ollama, make sure it's running locally and accessible.\n"
            f"If using OpenAI, check your API key is set in the OPENAI_API_KEY environment variable.",
        )

    def export_data(self):
        """Export activity data to a file."""
        # Ask user for file location and format
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Activity Data",
            os.path.expanduser("~/activities_export.json"),
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)",
        )

        if not file_path:
            return  # User cancelled

        try:
            success = False

            # Use the database's export methods if available
            if hasattr(self.activities_db, "export_activities_to_json") and hasattr(
                self.activities_db, "export_activities_to_text"
            ):
                if file_path.lower().endswith(".json"):
                    success = self.activities_db.export_activities_to_json(file_path)
                else:
                    success = self.activities_db.export_activities_to_text(file_path)
            else:
                # Fallback to our own implementation
                # Get all activities from the database
                all_activities = []

                # If we have a specific date range selected, use those activities
                if self.current_activities:
                    activities_to_export = self.current_activities
                    date_range = self.current_date_range
                else:
                    # Otherwise, get all activities from the database
                    # Get activities for the last year as a reasonable default
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=365)

                    current_date = start_date
                    while current_date <= end_date:
                        day_start = datetime(
                            current_date.year, current_date.month, current_date.day
                        )
                        day_activities = self.activities_db.get_activities_for_day(day_start)
                        all_activities.extend(day_activities)
                        current_date += timedelta(days=1)

                    activities_to_export = all_activities
                    date_range = "All Time"

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
                    self,
                    "Export Successful",
                    f"Successfully exported activities to {file_path}",
                )
            else:
                QMessageBox.warning(
                    self,
                    "Export Warning",
                    f"The export may not have completed successfully. Please check the file at {file_path}",
                )

        except Exception as e:
            QMessageBox.critical(
                self, "Export Error", f"An error occurred during export: {str(e)}"
            )

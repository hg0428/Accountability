"""
Analysis Widget for Accountability App.
Provides AI-powered analysis of user activities and patterns.
"""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QComboBox,
    QFrame,
    QProgressBar,
    QSplitter,
    QScrollArea,
    QMessageBox,
    QFileDialog,
    QCalendarWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QDate
from PyQt6.QtGui import QFont, QIcon

from ..ai_analysis import AIAnalyzer
import os
import json


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

    def __init__(self, database, parent=None):
        """Initialize the analysis widget."""
        super().__init__(parent)

        self.db = database

        # Get the database path from the main database
        db_path = None
        if hasattr(self.db, "db_path"):
            db_path = self.db.db_path

        self.analyzer = AIAnalyzer(db_path=db_path)
        self.current_analysis = None
        self.worker = None
        self.current_activities = []
        self.current_date_range = "Today"

        # Auto-load the last analysis on startup
        self.auto_load_last_analysis = True

        self.init_ui()

        # Auto-load the last analysis if enabled
        if self.auto_load_last_analysis:
            self.start_analysis(force_reload=False)

    def init_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create a scroll area for the entire content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Create a widget to hold all the scrollable content
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title and controls section
        header_frame = QFrame()
        header_frame.setObjectName("card")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(16)
        
        # Title
        title = QLabel("AI Activity Analysis")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)

        # Controls section
        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(12)

        # Date range selector
        date_label = QLabel("Time Period:")
        date_label.setObjectName("sectionTitle")
        controls_layout.addWidget(date_label)

        self.date_combo = QComboBox()
        self.date_combo.addItems(
            ["Today", "Yesterday", "This Week", "Last Week", "Last Month", "Custom Range"]
        )
        self.date_combo.setMinimumWidth(150)
        controls_layout.addWidget(self.date_combo)

        # API selector
        api_label = QLabel("AI Model:")
        api_label.setObjectName("sectionTitle")
        controls_layout.addWidget(api_label)

        self.api_combo = QComboBox()
        self.api_combo.addItems(["OpenAI", "Ollama (Local)"])
        controls_layout.addWidget(self.api_combo)

        # Analyze button
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.setObjectName("primaryButton")
        self.analyze_button.clicked.connect(self.force_reload_analysis)
        controls_layout.addWidget(self.analyze_button)

        # Export button
        export_button = QPushButton("Export Data")
        export_button.setObjectName("secondaryButton")
        export_button.clicked.connect(self.export_data)
        controls_layout.addWidget(export_button)

        header_layout.addWidget(controls_frame)
        layout.addWidget(header_frame)

        # Date range picker (initially hidden)
        self.date_range_container = QFrame()
        self.date_range_container.setObjectName("card")
        date_range_layout = QHBoxLayout(self.date_range_container)
        date_range_layout.setContentsMargins(12, 12, 12, 12)
        date_range_layout.setSpacing(12)
        
        from_label = QLabel("From:")
        date_range_layout.addWidget(from_label)
        
        self.start_date_calendar = QCalendarWidget()
        self.start_date_calendar.setGridVisible(True)
        self.start_date_calendar.setMaximumWidth(300)
        self.start_date_calendar.setMaximumHeight(250)
        date_range_layout.addWidget(self.start_date_calendar)
        
        to_label = QLabel("To:")
        date_range_layout.addWidget(to_label)
        
        self.end_date_calendar = QCalendarWidget()
        self.end_date_calendar.setGridVisible(True)
        self.end_date_calendar.setMaximumWidth(300)
        self.end_date_calendar.setMaximumHeight(250)
        date_range_layout.addWidget(self.end_date_calendar)
        
        apply_button = QPushButton("Apply Range")
        apply_button.setObjectName("primaryButton")
        apply_button.clicked.connect(self.apply_custom_date_range)
        date_range_layout.addWidget(apply_button)
        
        self.date_range_container.setVisible(False)
        layout.addWidget(self.date_range_container)

        # Progress indicator
        self.progress_container = QFrame()
        self.progress_container.setObjectName("infoCard")
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(16, 16, 16, 16)
        progress_layout.setSpacing(8)

        progress_label = QLabel("Analyzing your activities...")
        progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.progress_container.setVisible(False)
        layout.addWidget(self.progress_container)

        # Results container - will hold all the analysis cards
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(20)
        
        # Initially hide the results container
        self.results_container.setVisible(False)
        layout.addWidget(self.results_container)
        
        # Placeholder message when no analysis is available
        self.placeholder = QLabel("Select a time period and click 'Analyze' to see insights about your activities.")
        self.placeholder.setObjectName("placeholderText")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setWordWrap(True)
        self.placeholder.setMinimumHeight(200)
        layout.addWidget(self.placeholder)

        # Set the scroll content as the widget for the scroll area
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Connect date range change signal
        self.date_combo.currentIndexChanged.connect(self.on_date_range_changed)
        
        # Set default date range
        today = datetime.now().date()
        self.start_date_calendar.setSelectedDate(QDate.fromString((today - timedelta(days=7)).strftime("%Y-%m-%d"), "yyyy-MM-dd"))
        self.end_date_calendar.setSelectedDate(QDate.fromString(today.strftime("%Y-%m-%d"), "yyyy-MM-dd"))

    def on_date_range_changed(self, index):
        """Handle date range selection change."""
        # Hide date range picker by default
        self.date_range_container.setVisible(False)
        
        # If custom range is selected, show the date picker
        if index == 5:  # Custom Range
            self.date_range_container.setVisible(True)
            # No need to start analysis yet, wait for user to apply the range
        else:
            # For predefined ranges, start analysis immediately
            self.start_analysis(force_reload=False)
            
    def apply_custom_date_range(self):
        """Apply the custom date range and start analysis."""
        # Start analysis with the selected date range
        self.start_analysis(force_reload=False)

    def start_analysis(self, force_reload=False):
        """Start the AI analysis process."""
        # Show progress indicator
        self.progress_container.setVisible(True)
        self.analyze_button.setEnabled(False)

        # Get selected date range
        period_text = self.date_combo.currentText()

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
            day_activities = self.db.get_activities_for_day(day_start)
            activities.extend(day_activities)
            current_date += timedelta(days=1)

        self.current_activities = activities

        # Get daily notes for the date range
        notes_dict = {}
        if hasattr(self.db, "get_notes_for_date_range"):
            try:
                notes_dict = self.db.get_notes_for_date_range(start_date, end_date)
                print(f"Retrieved {len(notes_dict)} daily notes for analysis")
            except Exception as e:
                print(f"Error retrieving daily notes: {e}")

        # Set API type based on selection
        api_type = (
            "ollama" if self.api_combo.currentText() == "Ollama (Local)" else "openai"
        )

        # Store current date range
        self.current_date_range = period_text

        # Create and start worker thread
        self.worker = AnalysisWorker(
            self.analyzer, activities, period_text, force_reload, notes_dict
        )
        self.worker.analysis_complete.connect(self.update_analysis_results)
        self.worker.analysis_error.connect(self.handle_analysis_error)
        self.worker.finished.connect(lambda: self.analyze_button.setEnabled(True))
        self.worker.finished.connect(lambda: self.progress_container.setVisible(False))
        self.worker.start()

    def force_reload_analysis(self):
        """Force a reload of the analysis, ignoring any cached results."""
        self.start_analysis(force_reload=True)

    def update_analysis_results(self, results):
        """Update the UI with analysis results."""
        # Hide progress
        self.progress_container.setVisible(False)
        self.analyze_button.setEnabled(True)

        # Store current analysis
        self.current_analysis = results
        
        # Hide placeholder and show results container
        self.placeholder.setVisible(False)
        
        # Clear previous results
        self.clear_results_container()
        self.results_container.setVisible(True)
        
        # Create cards for each section of the analysis
        self.create_summary_card(results)
        self.create_patterns_card(results)
        self.create_insights_card(results)
        self.create_recommendations_card(results)
        self.create_productivity_card(results)
        
    def clear_results_container(self):
        """Clear all widgets from the results container."""
        # Remove all widgets from the results layout
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
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
        
        # Add to results layout
        self.results_layout.addWidget(card)
        
        return card
        
    def create_summary_card(self, results):
        """Create the summary card."""
        if "summary" not in results or not results["summary"]:
            return
            
        summary_text = QTextEdit()
        summary_text.setReadOnly(True)
        summary_text.setMinimumHeight(100)
        
        # Format the summary text with HTML
        try:
            summary_text.setHtml(results["summary"])
        except (ValueError, TypeError):
            summary_text.setPlainText(results["summary"])
            
        self.create_card("Activity Summary", summary_text)
        
    def create_patterns_card(self, results):
        """Create the patterns card."""
        if "patterns" not in results or not results["patterns"]:
            return
            
        patterns_text = QTextEdit()
        patterns_text.setReadOnly(True)
        patterns_text.setMinimumHeight(120)
        
        # Format the patterns as a bulleted list
        patterns_html = "<ul>"
        for pattern in results["patterns"]:
            patterns_html += f"<li>{pattern}</li>"
        patterns_html += "</ul>"
        
        patterns_text.setHtml(patterns_html)
        self.create_card("Activity Patterns", patterns_text)
        
    def create_insights_card(self, results):
        """Create the insights card."""
        if "insights" not in results or not results["insights"]:
            return
            
        insights_text = QTextEdit()
        insights_text.setReadOnly(True)
        insights_text.setMinimumHeight(150)
        
        # Format the insights as a bulleted list
        insights_html = "<ul>"
        for insight in results["insights"]:
            insights_html += f"<li>{insight}</li>"
        insights_html += "</ul>"
        
        insights_text.setHtml(insights_html)
        self.create_card("Key Insights", insights_text)
        
    def create_recommendations_card(self, results):
        """Create the recommendations card."""
        if "recommendations" not in results or not results["recommendations"]:
            return
            
        recommendations_text = QTextEdit()
        recommendations_text.setReadOnly(True)
        recommendations_text.setMinimumHeight(150)
        
        # Format the recommendations as a bulleted list
        recommendations_html = "<ul>"
        for recommendation in results["recommendations"]:
            recommendations_html += f"<li>{recommendation}</li>"
        recommendations_html += "</ul>"
        
        recommendations_text.setHtml(recommendations_html)
        self.create_card("Recommendations", recommendations_text)
        
    def create_productivity_card(self, results):
        """Create the productivity score card if available."""
        if "productivity_score" not in results:
            return
            
        try:
            score = float(results["productivity_score"])
            
            # Create a frame for the productivity score
            score_frame = QFrame()
            score_layout = QVBoxLayout(score_frame)
            score_layout.setContentsMargins(0, 0, 0, 0)
            score_layout.setSpacing(8)
            
            # Add score label
            score_label = QLabel(f"Productivity Score: {score:.1f}/10")
            score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            score_label.setObjectName("scoreLabel")
            score_layout.addWidget(score_label)
            
            # Add progress bar for visual representation
            score_bar = QProgressBar()
            score_bar.setRange(0, 100)
            score_bar.setValue(int(score * 10))
            score_bar.setTextVisible(False)
            score_layout.addWidget(score_bar)
            
            # Add explanation if available
            if "productivity_explanation" in results and results["productivity_explanation"]:
                explanation = QLabel(results["productivity_explanation"])
                explanation.setWordWrap(True)
                explanation.setAlignment(Qt.AlignmentFlag.AlignCenter)
                score_layout.addWidget(explanation)
                
            self.create_card("Productivity Score", score_frame)
        except (ValueError, TypeError):
            # Skip if score is not a valid number
            pass

    def handle_analysis_error(self, error_message):
        """Handle errors during analysis."""
        # Hide progress
        self.progress_container.setVisible(False)
        self.analyze_button.setEnabled(True)

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
                        day_activities = self.db.get_activities_for_day(day_start)
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

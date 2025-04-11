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
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QIcon

from ..ai_analysis import AIAnalyzer
import os
import json


class AnalysisWorker(QThread):
    """Worker thread for running AI analysis without blocking the UI."""

    analysis_complete = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)

    def __init__(self, analyzer, activities, date_range, force_reload=False, notes_dict=None):
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
                    print(f"Deleted cached analysis for {self.date_range} ({start_date.isoformat()} to {end_date.isoformat()})")
                conn.close()

            # Run the analysis
            print(f"Starting analysis for {self.date_range} with {len(self.activities)} activities")
            result = self.analyzer.analyze_activities(self.activities, self.date_range, notes_dict=self.notes_dict)
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title = QLabel("AI Activity Analysis")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Controls section
        controls_frame = QFrame()
        controls_frame.setObjectName("card")
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(20, 20, 20, 20)

        # Period selection
        period_label = QLabel("Analysis Period:")
        period_label.setObjectName("sectionTitle")

        self.period_combo = QComboBox()
        self.period_combo.addItems(
            ["Today", "Yesterday", "Last 3 Days", "Last Week", "Last Month"]
        )

        # API selection
        api_label = QLabel("AI Provider:")
        api_label.setObjectName("sectionTitle")

        self.api_combo = QComboBox()
        self.api_combo.addItems(["Ollama (Local)", "OpenAI"])

        # Analyze button
        self.analyze_button = QPushButton("Analyze Activities")
        self.analyze_button.setObjectName("successButton")
        self.analyze_button.clicked.connect(self.start_analysis)

        # Reload button
        self.reload_button = QPushButton("Force Reload")
        self.reload_button.setObjectName("secondaryButton")
        self.reload_button.setToolTip(
            "Force a new analysis even if cached results exist"
        )
        self.reload_button.clicked.connect(self.force_reload_analysis)

        # Export button
        self.export_button = QPushButton("Export Data")
        self.export_button.setObjectName("secondaryButton")
        self.export_button.setToolTip("Export your activity data to a file")
        self.export_button.clicked.connect(self.export_data)

        # Add controls to layout
        controls_layout.addWidget(period_label)
        controls_layout.addWidget(self.period_combo)
        controls_layout.addWidget(api_label)
        controls_layout.addWidget(self.api_combo)
        controls_layout.addWidget(self.analyze_button)
        controls_layout.addWidget(self.reload_button)
        controls_layout.addWidget(self.export_button)

        layout.addWidget(controls_frame)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results section
        results_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Summary
        summary_frame = QFrame()
        summary_frame.setObjectName("card")
        summary_layout = QVBoxLayout(summary_frame)
        summary_layout.setContentsMargins(20, 20, 20, 20)

        summary_title = QLabel("Summary")
        summary_title.setObjectName("sectionTitle")
        summary_layout.addWidget(summary_title)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlaceholderText("Analysis summary will appear here...")
        summary_layout.addWidget(self.summary_text)

        # Right side - Details
        details_frame = QFrame()
        details_frame.setObjectName("card")
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(20, 20, 20, 20)

        # Patterns section
        patterns_title = QLabel("Identified Patterns")
        patterns_title.setObjectName("sectionTitle")
        details_layout.addWidget(patterns_title)

        self.patterns_text = QTextEdit()
        self.patterns_text.setReadOnly(True)
        self.patterns_text.setPlaceholderText("Identified patterns will appear here...")
        self.patterns_text.setMaximumHeight(150)
        details_layout.addWidget(self.patterns_text)

        # Insights section
        insights_title = QLabel("Insights")
        insights_title.setObjectName("sectionTitle")
        details_layout.addWidget(insights_title)

        self.insights_text = QTextEdit()
        self.insights_text.setReadOnly(True)
        self.insights_text.setPlaceholderText("Insights will appear here...")
        self.insights_text.setMaximumHeight(150)
        details_layout.addWidget(self.insights_text)

        # Recommendations section
        recommendations_title = QLabel("Recommendations")
        recommendations_title.setObjectName("sectionTitle")
        details_layout.addWidget(recommendations_title)

        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        self.recommendations_text.setPlaceholderText(
            "Recommendations will appear here..."
        )
        details_layout.addWidget(self.recommendations_text)

        # Add frames to splitter
        results_splitter.addWidget(summary_frame)
        results_splitter.addWidget(details_frame)
        results_splitter.setSizes([400, 600])

        layout.addWidget(results_splitter)

    def start_analysis(self, force_reload=False):
        """Start the AI analysis process."""
        # Get selected period
        period_text = self.period_combo.currentText()
        self.current_date_range = period_text

        # Calculate date range based on selected period
        end_date = datetime.now()

        if period_text == "Today":
            start_date = datetime(end_date.year, end_date.month, end_date.day)
        elif period_text == "Yesterday":
            yesterday = end_date - timedelta(days=1)
            start_date = datetime(
                yesterday.year, yesterday.month, yesterday.day
            )
            end_date = datetime(
                yesterday.year, yesterday.month, yesterday.day, 23, 59, 59
            )
        elif period_text == "Last 3 Days":
            start_date = end_date - timedelta(days=3)
        elif period_text == "Last Week":
            start_date = end_date - timedelta(days=7)
        elif period_text == "Last Month":
            start_date = end_date - timedelta(days=30)
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

        # Check if there are activities to analyze
        if not activities:
            QMessageBox.information(
                self,
                "No Activities",
                f"No activities found for {period_text}. Please select a different period or record some activities.",
            )
            return

        # Get daily notes for the date range
        notes_dict = {}
        if hasattr(self.db, 'get_notes_for_date_range'):
            try:
                notes_dict = self.db.get_notes_for_date_range(start_date, end_date)
                print(f"Retrieved {len(notes_dict)} daily notes for analysis")
            except Exception as e:
                print(f"Error retrieving daily notes: {e}")

        # Set API type based on selection
        api_type = (
            "ollama" if self.api_combo.currentText() == "Ollama (Local)" else "openai"
        )

        # Update the analyzer with the current API type and database path
        db_path = None
        if hasattr(self.db, "db_path"):
            db_path = self.db.db_path
        self.analyzer = AIAnalyzer(api_type=api_type, db_path=db_path)

        # Show progress
        self.progress_bar.setVisible(True)
        self.analyze_button.setEnabled(False)
        self.reload_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.analyze_button.setText("Analyzing...")

        # Clear previous results
        self.summary_text.clear()
        self.patterns_text.clear()
        self.insights_text.clear()
        self.recommendations_text.clear()

        # Start analysis in a separate thread
        self.worker = AnalysisWorker(
            self.analyzer, activities, period_text, force_reload, notes_dict
        )
        self.worker.analysis_complete.connect(self.update_analysis_results)
        self.worker.analysis_error.connect(self.handle_analysis_error)
        self.worker.start()

    def force_reload_analysis(self):
        """Force a reload of the analysis, ignoring any cached results."""
        self.start_analysis(force_reload=True)

    def update_analysis_results(self, results):
        """Update the UI with analysis results."""
        # Hide progress
        self.progress_bar.setVisible(False)
        self.analyze_button.setEnabled(True)
        self.reload_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.analyze_button.setText("Analyze Activities")

        # Store current analysis
        self.current_analysis = results

        # Update summary
        self.summary_text.setHtml(f"<p>{results['summary']}</p>")
        
        # Add timestamp if available
        if 'created_at' in results:
            try:
                created_time = datetime.fromisoformat(results['created_at'])
                timestamp_html = f"<p><small>Analysis from: {created_time.strftime('%Y-%m-%d %H:%M:%S')}</small></p>"
                self.summary_text.append(timestamp_html)
            except (ValueError, TypeError):
                pass

        # Update patterns
        patterns_html = "<ul>"
        for pattern in results["patterns"]:
            patterns_html += f"<li>{pattern}</li>"
        patterns_html += "</ul>"
        self.patterns_text.setHtml(patterns_html)

        # Update insights
        insights_html = "<ul>"
        for insight in results["insights"]:
            insights_html += f"<li>{insight}</li>"
        insights_html += "</ul>"
        self.insights_text.setHtml(insights_html)

        # Update recommendations
        recommendations_html = "<ul>"
        for recommendation in results["recommendations"]:
            recommendations_html += f"<li>{recommendation}</li>"
        recommendations_html += "</ul>"
        self.recommendations_text.setHtml(recommendations_html)

    def handle_analysis_error(self, error_message):
        """Handle errors during analysis."""
        # Hide progress
        self.progress_bar.setVisible(False)
        self.analyze_button.setEnabled(True)
        self.reload_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.analyze_button.setText("Analyze Activities")

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

"""
Database Module for Accountability App.
Handles persistence of activities and settings.
"""

import os
import sqlite3
from datetime import datetime


class Database:
    """Handles database operations for the Accountability app."""

    def __init__(self, db_path=None):
        """Initialize the database connection."""
        if db_path is None:
            # Use a file in the user's home directory by default
            home_dir = os.path.expanduser("~")
            app_dir = os.path.join(home_dir, ".accountability")

            # Create directory if it doesn't exist
            if not os.path.exists(app_dir):
                os.makedirs(app_dir)

            db_path = os.path.join(app_dir, "accountability.db")

        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def initialize(self):
        """Initialize the database connection and tables."""
        self.conn = sqlite3.connect(self.db_path)
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Use Row as the row factory
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        # Create tables if they don't exist
        self._create_tables()

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def _create_tables(self):
        """Create the necessary database tables if they don't exist."""
        # Activities table
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            hour DATETIME NOT NULL,
            activity TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # Daily notes table
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS daily_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            notes TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        # Settings table
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
        )

        # Create index on hour for faster queries
        self.cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_activities_hour ON activities(hour)
        """
        )

        # Create index on date for faster queries
        self.cursor.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_daily_notes_date ON daily_notes(date)
        """
        )

        self.conn.commit()

    def get_last_activity_time(self):
        """Get the datetime of the last recorded activity."""
        self.cursor.execute(
            """
        SELECT hour FROM activities ORDER BY hour DESC LIMIT 1
        """
        )
        result = self.cursor.fetchone()

        if result:
            # Convert string to datetime
            return datetime.fromisoformat(result[0])
        return None

    def has_activity_for_hour(self, hour):
        """
        Check if there is an activity recorded for the given hour.

        Args:
            hour: datetime object representing the hour to check

        Returns:
            bool: True if an activity exists, False otherwise
        """
        hour_str = hour.isoformat()
        self.cursor.execute(
            """
        SELECT COUNT(*) FROM activities WHERE hour = ?
        """,
            (hour_str,),
        )

        count = self.cursor.fetchone()[0]
        return count > 0

    def add_activity(self, hour, activity_text):
        """
        Add or update an activity for the specified hour.

        Args:
            hour: datetime object representing when the activity occurred
            activity_text: Description of the activity
        """
        now = datetime.now().isoformat()
        hour_str = hour.isoformat()

        print(f"DB DEBUG: Adding activity '{activity_text}' for hour {hour_str}")

        # Check if an activity already exists for this hour
        self.cursor.execute(
            """
        SELECT id FROM activities WHERE hour = ?
        """,
            (hour_str,),
        )

        existing = self.cursor.fetchone()

        if existing:
            # Update existing activity
            print(f"DB DEBUG: Updating existing activity with ID {existing[0]}")
            self.cursor.execute(
                """
            UPDATE activities 
            SET timestamp = ?, activity = ? 
            WHERE id = ?
            """,
                (now, activity_text, existing[0]),
            )
        else:
            # Insert new activity
            print(f"DB DEBUG: Inserting new activity")
            self.cursor.execute(
                """
            INSERT INTO activities (timestamp, hour, activity)
            VALUES (?, ?, ?)
            """,
                (now, hour_str, activity_text),
            )

        self.conn.commit()
        print(f"DB DEBUG: Transaction committed")

    def get_activities_for_day(self, date):
        """
        Get all activities for a specific day.

        Args:
            date: A datetime object representing the day to retrieve

        Returns:
            A list of activity dictionaries
        """
        # Start and end of the day
        start_day = datetime(date.year, date.month, date.day, 0, 0, 0).isoformat()
        end_day = datetime(date.year, date.month, date.day, 23, 59, 59).isoformat()

        # Use a subquery to get the most recent activity for each hour
        self.cursor.execute(
            """
        SELECT a.id, a.timestamp, a.hour, a.activity 
        FROM activities a
        JOIN (
            SELECT hour, MAX(timestamp) as max_timestamp
            FROM activities
            WHERE hour BETWEEN ? AND ?
            GROUP BY hour
        ) b ON a.hour = b.hour AND a.timestamp = b.max_timestamp
        ORDER BY a.hour ASC
        """,
            (start_day, end_day),
        )

        activities = []
        for row in self.cursor.fetchall():
            activities.append(
                {
                    "id": row[0],
                    "timestamp": datetime.fromisoformat(row[1]),
                    "hour": datetime.fromisoformat(row[2]),
                    "activity": row[3],
                }
            )

        return activities

    def get_activities_for_date_range(self, start_date, end_date):
        """
        Get all activities between two dates, inclusive.

        Args:
            start_date: A datetime object representing the start day
            end_date: A datetime object representing the end day

        Returns:
            A list of activity dictionaries grouped by day
        """
        # Start and end of the day
        start_day = datetime(
            start_date.year, start_date.month, start_date.day, 0, 0, 0
        ).isoformat()
        end_day = datetime(
            end_date.year, end_date.month, end_date.day, 23, 59, 59
        ).isoformat()

        # Use a subquery to get the most recent activity for each hour
        self.cursor.execute(
            """
        SELECT a.id, a.timestamp, a.hour, a.activity 
        FROM activities a
        JOIN (
            SELECT hour, MAX(timestamp) as max_timestamp
            FROM activities
            WHERE hour BETWEEN ? AND ?
            GROUP BY hour
        ) b ON a.hour = b.hour AND a.timestamp = b.max_timestamp
        ORDER BY a.hour ASC
        """,
            (start_day, end_day),
        )

        activities = []
        for row in self.cursor.fetchall():
            activities.append(
                {
                    "id": row[0],
                    "timestamp": datetime.fromisoformat(row[1]),
                    "hour": datetime.fromisoformat(row[2]),
                    "activity": row[3],
                }
            )

        return activities

    def get_all_activities(self):
        """
        Get all activities in the database.

        Returns:
            A list of all activity dictionaries
        """
        # Use a subquery to get the most recent activity for each hour
        self.cursor.execute(
            """
        SELECT a.id, a.timestamp, a.hour, a.activity 
        FROM activities a
        JOIN (
            SELECT hour, MAX(timestamp) as max_timestamp
            FROM activities
            GROUP BY hour
        ) b ON a.hour = b.hour AND a.timestamp = b.max_timestamp
        ORDER BY a.hour ASC
        """
        )

        activities = []
        for row in self.cursor.fetchall():
            activities.append(
                {
                    "id": row[0],
                    "timestamp": datetime.fromisoformat(row[1]),
                    "hour": datetime.fromisoformat(row[2]),
                    "activity": row[3],
                }
            )

        return activities

    def export_activities_to_json(self, file_path):
        """
        Export all activities and daily notes to a JSON file.

        Args:
            file_path: Path to save the JSON file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import json

            activities = self.get_all_activities()

            # Format activities for export
            formatted_activities = []
            for activity in activities:
                formatted_activities.append(
                    {
                        "id": activity["id"],
                        "date": activity["hour"].strftime("%Y-%m-%d"),
                        "time": activity["hour"].strftime("%H:%M"),
                        "activity": activity["activity"],
                        "recorded_at": activity["timestamp"].isoformat(),
                    }
                )

            # Get all dates from activities
            all_dates = set(
                activity["hour"].strftime("%Y-%m-%d") for activity in activities
            )

            # Get all daily notes
            daily_notes = []
            for date_str in all_dates:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                note = self.get_daily_note(date_obj)
                if note:  # Only include non-empty notes
                    daily_notes.append({"date": date_str, "notes": note})

            # Prepare export data
            export_data = {
                "export_date": datetime.now().isoformat(),
                "total_activities": len(formatted_activities),
                "total_notes": len(daily_notes),
                "activities": formatted_activities,
                "daily_notes": daily_notes,
            }

            # Write to file
            with open(file_path, "w") as f:
                json.dump(export_data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error exporting activities: {e}")
            return False

    def export_activities_to_text(self, file_path):
        """
        Export all activities and daily notes to a text file.

        Args:
            file_path: Path to save the text file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            activities = self.get_all_activities()

            # Group by date
            activities_by_date = {}
            for activity in activities:
                date_str = activity["hour"].strftime("%Y-%m-%d")
                if date_str not in activities_by_date:
                    activities_by_date[date_str] = []
                activities_by_date[date_str].append(activity)

            # Get all daily notes for the dates
            notes_by_date = {}
            for date_str in activities_by_date.keys():
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                note = self.get_daily_note(date_obj)
                if note:  # Only include non-empty notes
                    notes_by_date[date_str] = note

            # Write to file
            with open(file_path, "w") as f:
                f.write("Accountability App - Activity Export\n")
                f.write(
                    f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                f.write(f"Total activities: {len(activities)}\n")
                f.write(f"Total daily notes: {len(notes_by_date)}\n\n")

                for date_str, day_activities in sorted(activities_by_date.items()):
                    f.write(f"=== {date_str} ===\n")

                    # Sort by hour
                    day_activities.sort(key=lambda x: x["hour"])

                    for activity in day_activities:
                        time_str = activity["hour"].strftime("%H:%M")
                        f.write(f"{time_str}: {activity['activity']}\n")

                    # Add daily note if it exists
                    if date_str in notes_by_date:
                        f.write("\nDAILY NOTE:\n")
                        f.write(f"{notes_by_date[date_str]}\n")

                    f.write("\n")

            return True
        except Exception as e:
            print(f"Error exporting activities: {e}")
            return False

    def save_daily_note(self, date, note_text):
        """
        Save or update a daily note.

        Args:
            date: A datetime object representing the day for the note
            note_text: The note text content

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Format date as ISO string (YYYY-MM-DD)
            date_str = date.strftime("%Y-%m-%d")
            now = datetime.now().isoformat()

            # Check if a note already exists for this date
            self.cursor.execute(
                """
            SELECT id FROM daily_notes WHERE date = ?
            """,
                (date_str,),
            )

            existing = self.cursor.fetchone()

            if existing:
                # Update existing note
                self.cursor.execute(
                    """
                UPDATE daily_notes 
                SET notes = ?, updated_at = ? 
                WHERE id = ?
                """,
                    (note_text, now, existing[0]),
                )
            else:
                # Insert new note
                self.cursor.execute(
                    """
                INSERT INTO daily_notes (date, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                    (date_str, note_text, now, now),
                )

            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving daily note: {e}")
            return False

    def get_daily_note(self, date):
        """
        Get the daily note for a specific date.

        Args:
            date: A datetime object representing the day to retrieve

        Returns:
            The note text or empty string if no note exists
        """
        try:
            # Format date as ISO string (YYYY-MM-DD)
            date_str = date.strftime("%Y-%m-%d")

            self.cursor.execute(
                """
            SELECT notes FROM daily_notes WHERE date = ?
            """,
                (date_str,),
            )

            result = self.cursor.fetchone()
            if result:
                return result[0]
            return ""
        except Exception as e:
            print(f"Error retrieving daily note: {e}")
            return ""

    def get_notes_for_date_range(self, start_date, end_date):
        """
        Get all notes between two dates, inclusive.

        Args:
            start_date: A datetime object representing the start day
            end_date: A datetime object representing the end day

        Returns:
            A dictionary with dates as keys and note texts as values
        """
        try:
            # Format dates as ISO strings (YYYY-MM-DD)
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")

            self.cursor.execute(
                """
            SELECT date, notes FROM daily_notes 
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC
            """,
                (start_date_str, end_date_str),
            )

            notes_dict = {}
            for row in self.cursor.fetchall():
                notes_dict[row[0]] = row[1]

            return notes_dict
        except Exception as e:
            print(f"Error retrieving notes for date range: {e}")
            return {}

    def update_setting(self, key, value):
        """
        Update a setting in the database.

        Args:
            key: Setting key
            value: Setting value
        """
        self.cursor.execute(
            """
        INSERT OR REPLACE INTO settings (key, value)
        VALUES (?, ?)
        """,
            (key, value),
        )

        self.conn.commit()

    def get_setting(self, key, default=None):
        """
        Get a setting from the database.

        Args:
            key: Setting key
            default: Default value if setting doesn't exist

        Returns:
            The setting value or the default
        """
        self.cursor.execute(
            """
        SELECT value FROM settings WHERE key = ?
        """,
            (key,),
        )

        result = self.cursor.fetchone()
        if result:
            return result[0]
        return default

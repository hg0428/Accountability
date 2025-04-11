"""
Activity Scheduler Module for Accountability App.
Manages time tracking and scheduling of hourly reminders.
"""

from datetime import datetime, timedelta
import time
from PyQt6.QtCore import QObject, pyqtSignal


class ActivityScheduler(QObject):
    """
    Manages the scheduling of activity reminders and tracking of missed hours.
    """
    
    reminder_due = pyqtSignal(list)  # Signal emitted when reminders are due
    missed_hours_changed = pyqtSignal(int)  # Signal emitted when missed hours count changes
    
    def __init__(self, database):
        """Initialize the scheduler with the database connection."""
        super().__init__()
        self.db = database
        self.last_check_time = None
        self.current_hour = None
        self.is_initialized = False
        self.missed_hours_count = 0
    
    def initialize(self):
        """Initialize the scheduler with data from the database."""
        # Get the last recorded activity time from the database
        self.last_recorded_time = self.db.get_last_activity_time()
        
        # If we have no recorded activities yet, start from the current hour
        if not self.last_recorded_time:
            now = datetime.now()
            self.last_recorded_time = datetime(
                now.year, now.month, now.day, now.hour, 0, 0
            )
        
        self.last_check_time = datetime.now()
        self.current_hour = self._get_current_hour()
        self.is_initialized = True
        
        # Check for missed hours immediately upon initialization
        missed = self.get_missed_hours()
        self.missed_hours_count = len(missed)
        self.missed_hours_changed.emit(self.missed_hours_count)
    
    def refresh_schedule(self):
        """Refresh the schedule state."""
        self.last_recorded_time = self.db.get_last_activity_time()
        self.last_check_time = datetime.now()
        self.current_hour = self._get_current_hour()
        
        # Update missed hours count
        missed = self.get_missed_hours()
        if len(missed) != self.missed_hours_count:
            self.missed_hours_count = len(missed)
            self.missed_hours_changed.emit(self.missed_hours_count)
    
    def get_missed_hours(self):
        """
        Check for missed hours that need to be filled in.
        Returns a list of datetime objects representing missed hours.
        """
        if not self.is_initialized:
            self.initialize()
        
        now = datetime.now()
        current_hour = self._get_current_hour()
        
        # Always check for missed entries when this method is called
        # or if it's been more than 5 minutes since our last check
        if True or current_hour != self.current_hour or (now - self.last_check_time).total_seconds() > 300:
            self.current_hour = current_hour
            self.last_check_time = now
            
            # Calculate all hours between last recorded time and now
            missed_hours = []
            
            # Start checking from the hour after the last recorded activity
            if self.last_recorded_time:
                check_hour = self.last_recorded_time + timedelta(hours=1)
            else:
                # If no activities recorded yet, start from the beginning of the current day
                check_hour = datetime(now.year, now.month, now.day, 0, 0, 0)
            
            # Check all hours up to the current hour
            while check_hour <= current_hour:
                # Check if this hour has an entry in the database
                if not self.db.has_activity_for_hour(check_hour):
                    missed_hours.append(check_hour)
                check_hour += timedelta(hours=1)
            
            # Update the missed hours count and notify listeners
            if len(missed_hours) != self.missed_hours_count:
                self.missed_hours_count = len(missed_hours)
                self.missed_hours_changed.emit(self.missed_hours_count)
            
            return missed_hours
        
        return []
    
    def record_activity(self, hours, activity_text):
        """
        Record an activity for the specified hours.
        
        Args:
            hours: List of datetime objects representing the hours to record
            activity_text: The activity description text
        """
        print(f"SCHEDULER DEBUG: Recording activity '{activity_text}' for {len(hours)} hours")
        for hour in hours:
            print(f"SCHEDULER DEBUG: Recording for hour {hour}")
            self.db.add_activity(hour, activity_text)
        
        # Update the last recorded time if needed
        if hours:
            latest_hour = max(hours)
            if not self.last_recorded_time or latest_hour > self.last_recorded_time:
                self.last_recorded_time = latest_hour
                print(f"SCHEDULER DEBUG: Updated last_recorded_time to {self.last_recorded_time}")
        
        # Refresh the schedule to update missed hours count
        self.refresh_schedule()
        print(f"SCHEDULER DEBUG: Schedule refreshed")
    
    def get_missed_hours_count(self):
        """Get the current count of missed hours."""
        return self.missed_hours_count
    
    def _get_current_hour(self):
        """Get a datetime representing the current hour with minutes/seconds set to 0."""
        now = datetime.now()
        return datetime(now.year, now.month, now.day, now.hour, 0, 0)

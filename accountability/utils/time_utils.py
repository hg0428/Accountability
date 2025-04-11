"""
Time utility functions for the Accountability app.
"""

from datetime import datetime, timedelta


def get_current_hour():
    """
    Get a datetime representing the current hour with minutes/seconds set to 0.
    
    Returns:
        datetime: The current hour
    """
    now = datetime.now()
    return datetime(now.year, now.month, now.day, now.hour, 0, 0)


def format_hour_range(hour):
    """
    Format a datetime hour into a readable hour range string.
    
    Args:
        hour: A datetime object representing the start hour
        
    Returns:
        str: Formatted hour range (e.g. "9:00 AM - 10:00 AM")
    """
    start_time = hour.strftime("%I:%M %p").lstrip("0")
    end_hour = hour + timedelta(hours=1)
    end_time = end_hour.strftime("%I:%M %p").lstrip("0")
    return f"{start_time} - {end_time}"


def get_hours_between(start_time, end_time):
    """
    Get a list of hour datetimes between start_time and end_time.
    
    Args:
        start_time: datetime representing the start hour
        end_time: datetime representing the end hour
        
    Returns:
        list: List of datetime objects representing each hour in the range
    """
    # Ensure we're working with hours only
    start_hour = datetime(start_time.year, start_time.month, start_time.day, 
                         start_time.hour, 0, 0)
    end_hour = datetime(end_time.year, end_time.month, end_time.day, 
                       end_time.hour, 0, 0)
    
    hours = []
    current = start_hour
    
    while current <= end_hour:
        hours.append(current)
        current += timedelta(hours=1)
    
    return hours


def get_day_start(dt):
    """
    Get a datetime representing the start of the day.
    
    Args:
        dt: A datetime object
        
    Returns:
        datetime: The start of the day (midnight)
    """
    return datetime(dt.year, dt.month, dt.day, 0, 0, 0)


def get_day_end(dt):
    """
    Get a datetime representing the end of the day.
    
    Args:
        dt: A datetime object
        
    Returns:
        datetime: The end of the day (23:59:59)
    """
    return datetime(dt.year, dt.month, dt.day, 23, 59, 59)

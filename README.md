# Accountability App

A desktop application that reminds you hourly to record your activities, helping you stay accountable and track how you spend your time.

## Features

- Hourly reminders to record your activities
- Tracks missed hours and prompts you to fill them in
- Multi-select functionality to quickly categorize blocks of time
- Daily activity summaries and history view
- System tray integration for minimal interruption

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/accountability.git
   cd accountability
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python main.py
   ```

## Usage

- The app will minimize to your system tray and show a popup every hour
- Record your activities by filling in the text field and clicking "Record"
- For multiple hours (such as when you start your day), select all applicable hours and enter one activity
- View your history by clicking "Open" or "View History" from the system tray menu
- Use the calendar to navigate to different days

## Requirements

- Python 3.7+
- PyQt6
- SQLite3

## Project Structure

```
accountability/
├── main.py                  # Application entry point
├── accountability/
│   ├── app.py               # Main application class
│   ├── scheduler.py         # Time tracking and scheduling
│   ├── database.py          # Data persistence
│   ├── ui/
│   │   ├── main_window.py   # Main UI window
│   │   ├── reminder.py      # Popup reminder
│   └── utils/
│       └── time_utils.py    # Time handling utilities
```

## Running on Startup

To have the application start automatically when you log in:

### macOS
1. Go to System Preferences > Users & Groups
2. Select your user and click "Login Items"
3. Click the "+" button and select the accountability app or a shortcut to `python main.py`

### Windows
1. Create a shortcut to `pythonw main.py` (use pythonw to run without a console window)
2. Press Win+R and type `shell:startup`
3. Copy the shortcut to the startup folder

## License

This project is licensed under the MIT License - see the LICENSE file for details.

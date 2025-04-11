"""
AI Analysis Module for Accountability App.
Provides AI-powered analysis of user activities and patterns.
"""

import json
import requests
from datetime import datetime, timedelta
import os
import sqlite3
from typing import Dict, List, Any, Optional, Union
import ollama
import psutil
import math

available_memory = psutil.virtual_memory().total * 0.7


class AIAnalyzer:
    """Class for analyzing user activities using AI."""

    def __init__(self, api_type="ollama", db_path=None):
        """
        Initialize the AI analyzer.

        Args:
            api_type: Type of AI API to use ('ollama' or 'openai')
            db_path: Path to the database file
        """
        self.api_type = api_type
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.api_endpoint = os.environ.get("OPENAI_ENDPOINT", "https://api.openai.com")
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.db_path = db_path

        # Initialize the database connection if path is provided
        if db_path:
            self.init_db()

        ollama_model_options = [
            {
                **model,
                "score": math.sqrt(model["size"]) * 100000
                + float(
                    str(datetime.fromisoformat(model["modified_at"]).timestamp())[2:]
                )
                * 500,
            }
            for model in ollama.list()["models"]
            if model["size"] < available_memory
        ]

        ollama_model_options.sort(key=lambda x: x["score"], reverse=True)
        print(ollama_model_options)
        self.model = os.environ.get(
            "AI_MODEL",
            (
                ollama_model_options[0]["name"]
                if api_type == "ollama"
                else "gpt-3.5-turbo"
            ),
        )

    def init_db(self):
        """Initialize the database for storing analysis results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create table for analysis results if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_range TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            api_type TEXT NOT NULL,
            model TEXT NOT NULL,
            summary TEXT,
            patterns TEXT,
            insights TEXT,
            recommendations TEXT,
            created_at TEXT NOT NULL
        )
        ''')
        
        # Create indices for faster lookups
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_analysis_date_range ON analysis_results(date_range, start_date, end_date)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_analysis_created_at ON analysis_results(created_at)
        ''')

        conn.commit()
        conn.close()

    def analyze_activities(
        self, activities: List[Dict[str, Any]], date_range: Optional[str] = None, notes_dict: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze user activities and generate insights.

        Args:
            activities: List of activity dictionaries with 'hour' and 'activity' keys
            date_range: String describing the date range (e.g., "Today", "This Week")
            notes_dict: Dictionary of daily notes with date strings as keys

        Returns:
            Dictionary with analysis results
        """
        if not activities:
            return {
                "summary": "No activities recorded for the selected period.",
                "patterns": [],
                "insights": [],
                "recommendations": [],
            }

        # Prepare activities for analysis
        formatted_activities = self._format_activities(activities, notes_dict)

        # Check if we have a saved analysis for this date range
        if self.db_path:
            saved_analysis = self.get_saved_analysis(date_range, activities)
            if saved_analysis:
                print(f"Using saved analysis for {date_range}")
                return saved_analysis

        # Generate prompt for AI
        prompt = self._generate_analysis_prompt(formatted_activities, date_range)

        # Get AI response
        try:
            if self.api_type == "ollama":
                response = self._query_ollama(prompt)
            else:
                response = self._query_openai(prompt)

            # Parse the response
            result = self._parse_ai_response(response)

            # Save the analysis result if we have a database connection
            if self.db_path:
                self.save_analysis(result, date_range, activities)
                print(f"Saved analysis for {date_range}")

            return result
        except Exception as e:
            print(f"Error analyzing activities: {e}")
            raise

    def get_saved_analysis(self, date_range: str, activities: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get saved analysis for the given date range and activities."""
        if not self.db_path:
            return None

        # Calculate date range
        start_date, end_date = self._get_date_range_bounds(date_range, activities)
        if not start_date or not end_date:
            return None

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get the most recent analysis for this date range
            cursor.execute('''
            SELECT id, summary, patterns, insights, recommendations, created_at 
            FROM analysis_results 
            WHERE date_range = ? AND start_date = ? AND end_date = ?
            ORDER BY created_at DESC LIMIT 1
            ''', (date_range, start_date.isoformat(), end_date.isoformat()))

            row = cursor.fetchone()
            conn.close()

            if row:
                analysis_id, summary, patterns, insights, recommendations, created_at = row
                print(f"Found saved analysis (ID: {analysis_id}) from {created_at}")
                
                try:
                    # Parse the JSON fields
                    return {
                        "summary": summary,
                        "patterns": json.loads(patterns),
                        "insights": json.loads(insights),
                        "recommendations": json.loads(recommendations),
                        "analysis_id": analysis_id,
                        "created_at": created_at
                    }
                except json.JSONDecodeError as e:
                    print(f"Error parsing saved analysis JSON: {e}")
                    return None

            return None
        except Exception as e:
            print(f"Error retrieving saved analysis: {e}")
            return None

    def save_analysis(self, result: Dict[str, Any], date_range: str, activities: List[Dict[str, Any]]):
        """Save analysis results to the database."""
        if not self.db_path:
            return

        # Calculate date range
        start_date, end_date = self._get_date_range_bounds(date_range, activities)
        if not start_date or not end_date:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if we already have an analysis for this exact date range
            cursor.execute('''
            SELECT id FROM analysis_results 
            WHERE date_range = ? AND start_date = ? AND end_date = ?
            ORDER BY created_at DESC LIMIT 1
            ''', (date_range, start_date.isoformat(), end_date.isoformat()))
            
            existing = cursor.fetchone()
            created_at = datetime.now().isoformat()
            
            if existing and 'analysis_id' in result:
                # Update existing analysis if we have an ID
                print(f"Updating existing analysis (ID: {existing[0]})")
                cursor.execute('''
                UPDATE analysis_results 
                SET summary = ?, patterns = ?, insights = ?, recommendations = ?, created_at = ?
                WHERE id = ?
                ''', (
                    result["summary"],
                    json.dumps(result["patterns"]),
                    json.dumps(result["insights"]),
                    json.dumps(result["recommendations"]),
                    created_at,
                    existing[0]
                ))
            else:
                # Insert new analysis
                print(f"Inserting new analysis for {date_range} ({start_date.isoformat()} to {end_date.isoformat()})")
                cursor.execute('''
                INSERT INTO analysis_results 
                (date_range, start_date, end_date, api_type, model, summary, patterns, insights, recommendations, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    date_range,
                    start_date.isoformat(),
                    end_date.isoformat(),
                    self.api_type,
                    self.model,
                    result["summary"],
                    json.dumps(result["patterns"]),
                    json.dumps(result["insights"]),
                    json.dumps(result["recommendations"]),
                    created_at
                ))

            conn.commit()
            conn.close()
            print(f"Analysis saved successfully")
        except Exception as e:
            print(f"Error saving analysis: {e}")

    def _get_date_range_bounds(self, date_range: str, activities: List[Dict[str, Any]]) -> tuple:
        """Get the start and end dates for a given date range."""
        if not activities:
            return None, None

        # Sort activities by hour
        sorted_activities = sorted(activities, key=lambda x: x["hour"])

        # If we have activities, use their actual date range
        if sorted_activities:
            start_date = sorted_activities[0]["hour"].replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = sorted_activities[-1]["hour"].replace(hour=23, minute=59, second=59, microsecond=999999)
            return start_date, end_date

        # Fallback to calculating based on date_range string
        now = datetime.now()
        end_date = now

        if date_range == "Today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == "Yesterday":
            yesterday = now - timedelta(days=1)
            start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif date_range == "Last 3 Days":
            start_date = (now - timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == "Last Week":
            start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == "Last Month":
            start_date = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        return start_date, end_date

    def _format_activities(
        self, activities: List[Dict[str, Any]], notes_dict: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Format activities for AI analysis."""
        formatted_activities = []
        
        # Group activities by date
        activities_by_date = {}
        for activity in activities:
            date_str = activity["hour"].strftime("%Y-%m-%d")
            if date_str not in activities_by_date:
                activities_by_date[date_str] = []
            activities_by_date[date_str].append(activity)
        
        # Format each date's activities
        for date_str, day_activities in sorted(activities_by_date.items()):
            day_dict = {
                "date": date_str,
                "activities": []
            }
            
            # Add daily note if available
            if notes_dict and date_str in notes_dict and notes_dict[date_str]:
                day_dict["notes"] = notes_dict[date_str]
            
            # Add activities
            for activity in sorted(day_activities, key=lambda x: x["hour"]):
                day_dict["activities"].append({
                    "time": activity["hour"].strftime("%H:%M"),
                    "activity": activity["activity"]
                })
            
            formatted_activities.append(day_dict)
        
        return formatted_activities

    def _generate_analysis_prompt(
        self, activities: List[Dict[str, Any]], date_range: Optional[str] = None
    ) -> str:
        """Generate a prompt for the AI based on user activities."""
        if not date_range:
            date_range = "the selected period"

        prompt = f"""
        Analyze the following daily activities for {date_range}:
        
        ```
        {json.dumps(activities, indent=2)}
        ```
        
        For each day, you have a list of activities with timestamps and possibly daily notes written by the user.
        
        Please provide a comprehensive analysis in JSON format with the following structure:
        {{
            "summary": "A paragraph summarizing overall patterns and insights",
            "patterns": [
                "Pattern 1",
                "Pattern 2",
                ...
            ],
            "insights": [
                "Insight 1",
                "Insight 2",
                ...
            ],
            "recommendations": [
                "Recommendation 1",
                "Recommendation 2",
                ...
            ]
        }}
        
        When analyzing, consider:
        1. Time management patterns
        2. Productivity trends
        3. Work-life balance
        4. Any user-provided notes and reflections for context
        5. Consistency and routine
        
        Make your analysis specific, actionable, and based directly on the data provided.
        """

        return prompt

    def _query_ollama(self, prompt: str) -> str:
        """Query the Ollama API with the given prompt."""
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant specialized in analyzing time usage and productivity patterns.",
                    },
                    {"role": "user", "content": prompt},
                ],
                format="json",
            )
            return response["message"]["content"]
        except Exception as e:
            print(f"Error querying Ollama: {e}")
            raise

    def _query_openai(self, prompt: str) -> str:
        """Query the OpenAI API with the given prompt."""
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not set. Please set the OPENAI_API_KEY environment variable."
            )

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an AI assistant specialized in analyzing time usage and productivity patterns.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                },
                timeout=60,
            )

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                raise Exception(
                    f"OpenAI API error: {response.status_code} - {response.text}"
                )
        except Exception as e:
            print(f"Error querying OpenAI: {e}")
            raise

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI response into a structured format."""
        try:
            # Try to extract JSON from the response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)

                # Ensure all required keys are present
                required_keys = ["summary", "patterns", "insights", "recommendations"]
                for key in required_keys:
                    if key not in result:
                        result[key] = (
                            [] if key != "summary" else "No analysis available."
                        )

                return result
            else:
                # Fallback: parse the text response manually
                return self._manual_parse_response(response)
        except Exception as e:
            print(f"Error parsing AI response: {e}")
            print(f"Raw response: {response}")
            return {
                "summary": "Failed to parse AI analysis.",
                "patterns": [],
                "insights": [],
                "recommendations": [],
            }

    def _manual_parse_response(self, response: str) -> Dict[str, Any]:
        """Manually parse the AI response if JSON parsing fails."""
        result = {"summary": "", "patterns": [], "insights": [], "recommendations": []}

        # Simple heuristic parsing
        lines = response.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()

            if not line:
                continue

            if "summary" in line.lower() and ":" in line:
                current_section = "summary"
                result["summary"] = line.split(":", 1)[1].strip()
            elif "pattern" in line.lower() and ":" in line:
                current_section = "patterns"
            elif "insight" in line.lower() and ":" in line:
                current_section = "insights"
            elif "recommendation" in line.lower() and ":" in line:
                current_section = "recommendations"
            elif current_section and current_section != "summary":
                # Check if line starts with a bullet point or number
                if (
                    line.startswith("-")
                    or line.startswith("*")
                    or (line[0].isdigit() and line[1:3] in (". ", ") "))
                ):
                    item = line.split(" ", 1)[1].strip()
                    result[current_section].append(item)
                elif result[current_section]:  # Append to the last item if it exists
                    result[current_section][-1] += " " + line

        return result

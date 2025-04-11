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
import re

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
        
        # Ensure the database has the correct schema
        if db_path:
            self._init_database()

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

    def _init_database(self):
        """Initialize the database schema if needed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if analysis_results table exists, create if not
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_range TEXT,
                start_date TEXT,
                end_date TEXT,
                api_type TEXT,
                model TEXT,
                summary TEXT,
                patterns TEXT,
                insights TEXT,
                recommendations TEXT,
                productivity_score REAL,
                productivity_explanation TEXT,
                created_at TEXT
            )
            """
        )
        
        # Check if the productivity_score column exists, add if not
        cursor.execute("PRAGMA table_info(analysis_results)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "productivity_score" not in columns:
            cursor.execute("ALTER TABLE analysis_results ADD COLUMN productivity_score REAL")
        
        if "productivity_explanation" not in columns:
            cursor.execute("ALTER TABLE analysis_results ADD COLUMN productivity_explanation TEXT")
        
        conn.commit()
        conn.close()

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
            productivity_score REAL,
            productivity_explanation TEXT,
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
        try:
            if not activities:
                return {
                    "summary": "No activities recorded for the selected period.",
                    "patterns": [],
                    "insights": [],
                    "recommendations": [],
                    "productivity_score": 0,
                    "productivity_explanation": "No activities to analyze"
                }

            # Prepare activities for analysis
            formatted_activities = self._format_activities(activities, notes_dict)
            
            if not formatted_activities:
                return {
                    "summary": "Could not process activities for the selected period.",
                    "patterns": [],
                    "insights": [],
                    "recommendations": [],
                    "productivity_score": 0,
                    "productivity_explanation": "No valid activities to analyze"
                }

            # Check if we have a saved analysis for this date range
            if self.db_path:
                saved_analysis = self.get_saved_analysis(date_range, activities)
                if saved_analysis:
                    print(f"Using saved analysis for {date_range}")
                    return saved_analysis

            # Generate prompt for AI
            prompt = self._generate_analysis_prompt(formatted_activities, date_range)

            # Query the appropriate AI API
            try:
                if self.api_type == "ollama":
                    response = self._query_ollama(prompt)
                else:
                    response = self._query_openai(prompt)

                # Parse the response
                result = self._parse_ai_response(response)

                # Save the analysis if we have a database connection
                if self.db_path:
                    self.save_analysis(result, date_range, activities)

                return result
            except Exception as e:
                print(f"Error in AI query: {e}")
                return {
                    "summary": f"Analysis failed: {str(e)}",
                    "patterns": [],
                    "insights": [],
                    "recommendations": [],
                    "productivity_score": 0,
                    "productivity_explanation": "Analysis failed: Could not query AI service"
                }
        except Exception as e:
            print(f"Error in analyze_activities: {e}")
            import traceback
            traceback.print_exc()
            return {
                "summary": f"Analysis failed: {str(e)}",
                "patterns": [],
                "insights": [],
                "recommendations": [],
                "productivity_score": 0,
                "productivity_explanation": "Analysis failed"
            }

    def get_saved_analysis(self, date_range: str, activities: List[Dict[str, Any]]):
        """Get saved analysis for the given date range and activities."""
        if not self.db_path:
            return None

        try:
            # Get date range bounds
            start_date, end_date = self._get_date_range_bounds(date_range, activities)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get the latest analysis for this date range
            cursor.execute('''
            SELECT id, summary, patterns, insights, recommendations, productivity_score, productivity_explanation, created_at 
            FROM analysis_results 
            WHERE date_range = ? 
            ORDER BY created_at DESC 
            LIMIT 1
            ''', (date_range,))
            
            row = cursor.fetchone()
            
            if row:
                analysis_id, summary, patterns, insights, recommendations, productivity_score, productivity_explanation, timestamp = row
                
                # Handle potential NULL values for productivity score and explanation
                if productivity_score is None:
                    productivity_score = 0.0
                else:
                    try:
                        productivity_score = float(productivity_score)
                    except (ValueError, TypeError):
                        productivity_score = 0.0
                
                if productivity_explanation is None:
                    productivity_explanation = ""
                
                print(f"Found saved analysis (ID: {analysis_id}) from {timestamp}")
                
                # Parse JSON strings if needed
                try:
                    patterns_list = json.loads(patterns) if patterns else []
                except:
                    patterns_list = []
                
                try:
                    insights_list = json.loads(insights) if insights else []
                except:
                    insights_list = []
                
                try:
                    recommendations_list = json.loads(recommendations) if recommendations else []
                except:
                    recommendations_list = []
                
                return {
                    "id": analysis_id,
                    "summary": summary,
                    "patterns": patterns_list,
                    "insights": insights_list,
                    "recommendations": recommendations_list,
                    "productivity_score": productivity_score,
                    "productivity_explanation": productivity_explanation,
                    "timestamp": timestamp
                }
            
            return None
        except Exception as e:
            print(f"Error retrieving saved analysis: {e}")
            return None

    def save_analysis(self, result: Dict[str, Any], date_range: str, activities: List[Dict[str, Any]]):
        """Save analysis results to database."""
        if not self.db_path:
            return

        # Get start and end dates from activities
        start_date, end_date = self._get_date_range_bounds(date_range, activities)
        
        if not start_date or not end_date:
            print("Cannot save analysis: invalid date range")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert lists to JSON strings for storage
            patterns_json = json.dumps(result.get("patterns", []))
            insights_json = json.dumps(result.get("insights", []))
            recommendations_json = json.dumps(result.get("recommendations", []))
            
            # Get productivity score and explanation
            productivity_score = result.get("productivity_score", 0)
            productivity_explanation = result.get("productivity_explanation", "")
            
            # Try to convert productivity_score to float
            try:
                productivity_score = float(productivity_score)
            except (ValueError, TypeError):
                productivity_score = 0.0
            
            # Insert the analysis results
            cursor.execute('''
            INSERT OR REPLACE INTO analysis_results 
            (id, date_range, start_date, end_date, api_type, model, summary, patterns, insights, recommendations, productivity_score, productivity_explanation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                None,
                date_range,
                start_date.isoformat(),
                end_date.isoformat(),
                self.api_type,
                self.model,
                result.get("summary", ""),
                patterns_json,
                insights_json,
                recommendations_json,
                productivity_score,
                productivity_explanation,
                datetime.now().isoformat()
            ))
            
            analysis_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"Saved analysis with ID: {analysis_id}")
            return analysis_id
        except Exception as e:
            print(f"Error saving analysis: {e}")
            return None

    def _get_date_range_bounds(self, date_range: str, activities: List[Dict[str, Any]]) -> tuple:
        """Get the start and end dates for a given date range."""
        if not activities:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return today, today.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Sort activities by hour, handling potential missing 'hour' key
        valid_activities = []
        for activity in activities:
            if "hour" in activity and activity["hour"] is not None:
                valid_activities.append(activity)
        
        if not valid_activities:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return today, today.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        sorted_activities = sorted(valid_activities, key=lambda x: x["hour"])

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
        
        # Filter out activities with missing or invalid 'hour' key
        valid_activities = []
        for activity in activities:
            if "hour" in activity and activity["hour"] is not None:
                valid_activities.append(activity)
        
        if not valid_activities:
            # Return an empty list if no valid activities
            return []
        
        # Group activities by date
        activities_by_date = {}
        for activity in valid_activities:
            try:
                date_str = activity["hour"].strftime("%Y-%m-%d")
                if date_str not in activities_by_date:
                    activities_by_date[date_str] = []
                activities_by_date[date_str].append(activity)
            except (AttributeError, TypeError) as e:
                # Skip activities with invalid hour format
                print(f"Skipping activity with invalid hour format: {activity.get('activity', 'Unknown')}")
                continue
        
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
                try:
                    day_dict["activities"].append({
                        "time": activity["hour"].strftime("%H:%M"),
                        "activity": activity["activity"]
                    })
                except (AttributeError, TypeError) as e:
                    # Skip activities with invalid hour format
                    print(f"Skipping activity time formatting: {activity.get('activity', 'Unknown')}")
                    continue
            
            formatted_activities.append(day_dict)
        
        return formatted_activities

    def _generate_analysis_prompt(
        self, activities: List[Dict[str, Any]], date_range: Optional[str] = None
    ) -> str:
        """Generate a prompt for the AI based on user activities."""
        # Format activities for the prompt
        activity_text = ""
        
        # Check if activities is using the new format (after _format_activities)
        if activities and "date" in activities[0] and "activities" in activities[0]:
            # Using the new format where activities are grouped by date
            for day in activities:
                date_str = day["date"]
                
                # Add daily note if available
                if "notes" in day and day["notes"]:
                    activity_text += f"## {date_str} Notes\n{day['notes']}\n\n"
                
                activity_text += f"## {date_str} Activities\n"
                for activity_item in day["activities"]:
                    time_str = activity_item["time"]
                    activity_desc = activity_item["activity"]
                    activity_text += f"- {date_str} {time_str}: {activity_desc}\n"
                activity_text += "\n"
        else:
            # Fallback for old format or direct activity list
            for activity in activities:
                try:
                    if "hour" in activity and activity["hour"]:
                        hour = activity["hour"]
                        activity_desc = activity.get("activity", "Unknown activity")
                        activity_text += f"- {hour.strftime('%Y-%m-%d %H:%M')}: {activity_desc}\n"
                except (AttributeError, KeyError, TypeError) as e:
                    print(f"Warning: Failed to format activity for prompt: {e}")
                    continue

        date_range_text = f" for {date_range}" if date_range else ""

        prompt = f"""Analyze the following activity log{date_range_text}:

{activity_text}

Please provide a comprehensive analysis in the following JSON format:
{{
"summary": "A paragraph summarizing the overall activity patterns and key insights",
"patterns": [
    "Pattern 1: Description of the first identified pattern",
    "Pattern 2: Description of the second identified pattern"
],
"insights": [
    "Insight 1: Description of the first key insight",
    "Insight 2: Description of the second key insight"
],
"recommendations": [
    "Recommendation 1: Specific actionable suggestion based on the analysis",
    "Recommendation 2: Another specific actionable suggestion"
],
"productivity_score": 7.5,
"productivity_explanation": "Brief explanation of how the productivity score was calculated"
}}

The productivity_score should be a number between 0 and 10, where 0 is completely unproductive and 10 is extremely productive. Base this score on factors like:
- Consistency of activities
- Balance between work and personal time
- Focus on important tasks
- Efficient use of time
- Presence of breaks and self-care

Provide at least 2-3 patterns, 2-3 insights, and 2-3 recommendations. Focus on actionable insights that can help improve productivity and work-life balance.
"""

        return prompt

    def _query_ollama(self, prompt: str) -> str:
        """Query the Ollama API with the given prompt."""
        try:
            print("Connecting to Ollama API...")
            print(f"Using model: {self.model}")
            print(f"Host: {self.ollama_host}")
            
            # Check if Ollama is running
            try:
                # Validate connection with a simple ping
                ollama.list()
                print("Successfully connected to Ollama")
            except Exception as conn_err:
                print(f"Failed to connect to Ollama: {conn_err}")
                raise RuntimeError(f"Could not connect to Ollama service: {conn_err}. Is Ollama running?")
            
            print("Sending prompt to Ollama for analysis...")
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
            print("Received response from Ollama")
            return response["message"]["content"]
        except Exception as e:
            print(f"Error querying Ollama: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to get analysis from Ollama: {e}")

    def _query_openai(self, prompt: str) -> str:
        """Query the OpenAI API with the given prompt."""
        try:
            print("Connecting to OpenAI API...")
            api_key = self.api_key
            
            if not api_key:
                raise ValueError("OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable.")
            
            print(f"Using model: {self.model}")
            print(f"API Endpoint: {self.api_endpoint}")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an AI assistant specialized in analyzing time usage and productivity patterns."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "response_format": {"type": "json_object"}
            }
            
            print("Sending request to OpenAI...")
            response = requests.post(
                f"{self.api_endpoint}/v1/chat/completions", 
                headers=headers, 
                json=payload
            )
            
            if response.status_code != 200:
                error_message = f"OpenAI API error: {response.status_code} - {response.text}"
                print(error_message)
                raise RuntimeError(error_message)
                
            print("Received response from OpenAI")
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            print(f"Error querying OpenAI: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to get analysis from OpenAI: {e}")

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
                required_keys = ["summary", "patterns", "insights", "recommendations", "productivity_score", "productivity_explanation"]
                for key in required_keys:
                    if key not in result:
                        if key == "summary":
                            result[key] = "No analysis available."
                        elif key == "productivity_score":
                            result[key] = 5.0
                        elif key == "productivity_explanation":
                            result[key] = "No explanation provided."
                        else:
                            result[key] = []

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
                "productivity_score": 0,
                "productivity_explanation": "Failed to parse analysis"
            }

    def _manual_parse_response(self, response: str) -> Dict[str, Any]:
        """Manually parse the AI response if JSON parsing fails."""
        result = {
            "summary": "", 
            "patterns": [], 
            "insights": [], 
            "recommendations": [],
            "productivity_score": 5.0,
            "productivity_explanation": ""
        }

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
            elif "productivity score" in line.lower() and ":" in line:
                current_section = "productivity_score"
                try:
                    score_text = line.split(":", 1)[1].strip()
                    # Extract the first number from the text
                    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", score_text)
                    if numbers:
                        result["productivity_score"] = float(numbers[0])
                except:
                    pass
            elif "productivity explanation" in line.lower() and ":" in line:
                current_section = "productivity_explanation"
                result["productivity_explanation"] = line.split(":", 1)[1].strip()
            elif current_section and current_section not in ["summary", "productivity_score", "productivity_explanation"]:
                # Check if line starts with a bullet point or number
                if (
                    line.startswith("-")
                    or line.startswith("*")
                    or (line[0].isdigit() and line[1:3] in (". ", ") "))
                ):
                    item = line.split(" ", 1)[1].strip() if " " in line else line
                    result[current_section].append(item)
                elif result[current_section]:  # Append to the last item if it exists
                    result[current_section][-1] += " " + line
            elif current_section == "productivity_explanation":
                result["productivity_explanation"] += " " + line

        return result

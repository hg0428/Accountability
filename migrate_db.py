#!/usr/bin/env python3
"""
Database migration script for Accountability app.
Adds productivity_score and productivity_explanation columns to analysis_results table.
"""

import sqlite3
import os
import sys

def migrate_database(db_path):
    """
    Migrate the database to add new columns for productivity score.
    
    Args:
        db_path: Path to the SQLite database file
    """
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the columns already exist
        cursor.execute("PRAGMA table_info(analysis_results)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add productivity_score column if it doesn't exist
        if "productivity_score" not in columns:
            print("Adding productivity_score column...")
            cursor.execute("ALTER TABLE analysis_results ADD COLUMN productivity_score REAL")
        else:
            print("productivity_score column already exists")
        
        # Add productivity_explanation column if it doesn't exist
        if "productivity_explanation" not in columns:
            print("Adding productivity_explanation column...")
            cursor.execute("ALTER TABLE analysis_results ADD COLUMN productivity_explanation TEXT")
        else:
            print("productivity_explanation column already exists")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print("Database migration completed successfully!")
        return True
    
    except Exception as e:
        print(f"Error during database migration: {e}")
        return False

if __name__ == "__main__":
    # Default database path
    default_db_path = os.path.join(os.path.expanduser("~"), ".accountability", "accountability.db")
    
    # Use command line argument if provided, otherwise use default path
    db_path = sys.argv[1] if len(sys.argv) > 1 else default_db_path
    
    print(f"Migrating database at: {db_path}")
    success = migrate_database(db_path)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

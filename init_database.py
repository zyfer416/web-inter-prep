#!/usr/bin/env python3
"""
Database initialization script for Web-Inter-Prep
This script creates the SQLite database with all required tables
"""

import sqlite3
import os
from datetime import datetime

def create_database():
    """Create the SQLite database with all required tables"""
    
    # Create database in the current directory
    db_path = 'interview_prep.db'
    print(f"Creating database at: {os.path.abspath(db_path)}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Users table created")
    
    # Attempts table for tracking user practice
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            correct BOOLEAN NOT NULL,
            user_answer TEXT,
            mock_session_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    print("✅ Attempts table created")
    
    # Mock interview sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mock_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            total_questions INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    print("✅ Mock sessions table created")
    
    # Add some sample data for testing
    try:
        # Check if we already have users
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            # Add a sample user for testing
            from werkzeug.security import generate_password_hash
            sample_password = generate_password_hash('password123')
            
            cursor.execute('''
                INSERT INTO users (name, email, password_hash) 
                VALUES (?, ?, ?)
            ''', ('Test User', 'test@example.com', sample_password))
            
            print("✅ Sample user created (test@example.com / password123)")
        
    except Exception as e:
        print(f"⚠️  Could not create sample data: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"🎉 Database initialization complete!")
    print(f"📁 Database file: {os.path.abspath(db_path)}")
    print(f"📊 Tables created: users, attempts, mock_sessions")

if __name__ == "__main__":
    create_database()

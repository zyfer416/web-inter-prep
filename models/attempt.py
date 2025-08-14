"""
Attempt Model - Data Access Layer
Handles all practice attempt-related database operations
"""

import sqlite3
from datetime import datetime

class Attempt:
    def __init__(self, db_path='interview_prep.db'):
        self.db_path = db_path
    
    def create_attempt(self, user_id, question_id, correct, user_answer):
        """Create a new practice attempt"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO attempts (user_id, question_id, correct, user_answer) VALUES (?, ?, ?, ?)',
            (user_id, question_id, correct, user_answer)
        )
        attempt_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return attempt_id
    
    def get_user_attempts(self, user_id):
        """Get all attempts for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM attempts WHERE user_id = ? ORDER BY timestamp DESC',
            (user_id,)
        )
        attempts = cursor.fetchall()
        conn.close()
        return attempts
    
    def get_user_stats(self, user_id):
        """Get user statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total questions attempted
        cursor.execute('SELECT COUNT(*) FROM attempts WHERE user_id = ?', (user_id,))
        total_attempted = cursor.fetchone()[0]
        
        # Correct answers
        cursor.execute('SELECT COUNT(*) FROM attempts WHERE user_id = ? AND correct = 1', (user_id,))
        correct_answers = cursor.fetchone()[0]
        
        # Calculate accuracy
        accuracy = (correct_answers / total_attempted * 100) if total_attempted > 0 else 0
        
        conn.close()
        
        return {
            'total_attempted': total_attempted,
            'correct_answers': correct_answers,
            'accuracy': accuracy
        }
    
    def get_weak_topics(self, user_id, limit=3):
        """Get user's weak topics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT question_id, COUNT(*) as incorrect_count
            FROM attempts 
            WHERE user_id = ? AND correct = 0
            GROUP BY question_id 
            ORDER BY incorrect_count DESC 
            LIMIT ?
        ''', (user_id, limit))
        weak_topics = cursor.fetchall()
        conn.close()
        return weak_topics

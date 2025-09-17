"""
User Model - Data Access Layer
Handles all user-related database operations
"""

import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User:
    def __init__(self, db_path='interview_prep.db'):
        self.db_path = db_path
    
    def create_user(self, name, email, password):
        """Create a new user"""
        password_hash = generate_password_hash(password)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                (name, email, password_hash)
            )
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            return None
    
    def authenticate_user(self, email, password):
        """Authenticate user login"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, name, password_hash FROM users WHERE email = ?', 
            (email,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            return {
                'id': user[0],
                'name': user[1],
                'email': email
            }
        return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, name, email, created_at FROM users WHERE id = ?', 
            (user_id,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'name': user[1],
                'email': user[2],
                'created_at': user[3]
            }
        return None

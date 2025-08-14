"""
Web-Inter-Prep - Refactored with 2-3 Tier Architecture
Main Flask Application File
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import json
import os
from datetime import datetime, timedelta
import random

# Import our layered architecture components
from services.user_service import UserService
from models.user import User
from models.attempt import Attempt

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Initialize services
user_service = UserService()

# Database initialization
def init_db():
    """Initialize the SQLite database with required tables"""
    conn = sqlite3.connect('interview_prep.db')
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
    
    # Attempts table for tracking user practice
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            correct BOOLEAN NOT NULL,
            user_answer TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
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
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# ===== TIER 1: PRESENTATION LAYER (ROUTES) =====

@app.route('/')
def home():
    """Home page route - Presentation Layer"""
    return render_template('home.html')

@app.route('/features')
def features():
    """Features showcase page - Presentation Layer"""
    return render_template('features.html')

@app.route('/career_roadmap')
def career_roadmap():
    """Career Roadmap Generator page - Presentation Layer"""
    return render_template('career_roadmap.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication - Presentation Layer"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Use service layer for business logic
        result = user_service.login_user(email, password)
        
        if result['success']:
            # Set session data
            session['user_id'] = result['user']['id']
            session['user_name'] = result['user']['name']
            flash(result['message'], 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(result['message'], 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page and user creation - Presentation Layer"""
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        # Use service layer for business logic
        result = user_service.register_user(name, email, password)
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('login'))
        else:
            flash(result['message'], 'error')
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    """User dashboard - Presentation Layer"""
    if 'user_id' not in session:
        flash('Please login to access dashboard', 'error')
        return redirect(url_for('login'))
    
    # Use service layer to get dashboard data
    dashboard_data = user_service.get_user_dashboard_data(session['user_id'])
    
    if not dashboard_data:
        flash('Error loading dashboard data', 'error')
        return redirect(url_for('home'))
    
    return render_template('dashboard.html', stats=dashboard_data)

@app.route('/practice')
def practice():
    """Practice questions page - Presentation Layer"""
    if 'user_id' not in session:
        flash('Please login to access practice', 'error')
        return redirect(url_for('login'))
    
    questions = load_questions()
    return render_template('practice.html', questions=questions)

@app.route('/dsa')
def dsa():
    """DSA Practice mode - Presentation Layer"""
    if 'user_id' not in session:
        flash('Please login to access DSA practice', 'error')
        return redirect(url_for('login'))
    return render_template('practice.html')

@app.route('/mock')
def mock_interview():
    """Mock interview page - Presentation Layer"""
    if 'user_id' not in session:
        flash('Please login to access mock interviews', 'error')
        return redirect(url_for('login'))
    return render_template('mock.html')

@app.route('/resources')
def resources():
    """Learning resources page - Presentation Layer"""
    # Static resources data
    resources_data = {
        'technical': [
            {
                'title': 'LeetCode',
                'description': 'Practice coding problems and algorithms',
                'url': 'https://leetcode.com',
                'type': 'Practice Platform'
            },
            {
                'title': 'Cracking the Coding Interview',
                'description': 'Comprehensive interview preparation book',
                'url': 'https://www.crackingthecodinginterview.com',
                'type': 'Book'
            }
        ],
        'behavioral': [
            {
                'title': 'STAR Method Guide',
                'description': 'Structure your behavioral interview answers',
                'url': 'https://www.indeed.com/career-advice/interviewing/how-to-use-the-star-interview-response-technique',
                'type': 'Article'
            }
        ]
    }
    
    return render_template('resources.html', resources=resources_data)

@app.route('/custom')
def custom_practice():
    """Custom practice session - Presentation Layer"""
    if 'user_id' not in session:
        flash('Please login to access custom practice', 'error')
        return redirect(url_for('login'))
    
    return render_template('custom_practice.html')

@app.route('/logout')
def logout():
    """Logout user - Presentation Layer"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

# ===== HELPER FUNCTIONS =====

def load_questions():
    """Load questions data - This would typically be in a Question model"""
    # This is a simplified version - in production, this would be in a database
    return [
        {
            'id': 1,
            'title': 'Two Sum',
            'description': 'Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.',
            'difficulty': 'easy',
            'category': 'Arrays',
            'leetcodeUrl': 'https://leetcode.com/problems/two-sum/',
            'solution': {
                'approach': 'Use a hash map to store complements.',
                'timeComplexity': 'O(n)',
                'spaceComplexity': 'O(n)',
                'code': 'function twoSum(nums, target) { /* ... */ }',
                'explanation': 'We iterate through the array once...'
            }
        }
    ]

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors - Presentation Layer"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors - Presentation Layer"""
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8081)

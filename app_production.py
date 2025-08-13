#!/usr/bin/env python3
"""
Web-Inter-Prep Production Application
Flask application for interview preparation platform
"""

import os
import sqlite3
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from config import config

# Initialize Flask app
app = Flask(__name__)

# Get configuration based on environment
config_name = os.environ.get('FLASK_ENV', 'production')
app.config.from_object(config[config_name])

# Ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect('interview_prep.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create attempts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id TEXT NOT NULL,
            correct BOOLEAN NOT NULL,
            user_answer TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create mock_sessions table
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

def load_questions():
    """Load questions from data file"""
    questions = [
        {
            'id': 1,
            'question': 'What is the time complexity of binary search?',
            'type': 'technical',
            'difficulty': 'medium',
            'hints': 'Think about how the search space is divided in each iteration.',
            'answer': 'O(log n) - The search space is halved in each iteration.'
        },
        {
            'id': 2,
            'question': 'Explain the difference between a stack and a queue.',
            'type': 'technical',
            'difficulty': 'easy',
            'hints': 'Consider the order of insertion and removal.',
            'answer': 'Stack: LIFO (Last In, First Out), Queue: FIFO (First In, First Out)'
        },
        {
            'id': 3,
            'question': 'What is the purpose of a hash table?',
            'type': 'technical',
            'difficulty': 'medium',
            'hints': 'Think about fast data retrieval.',
            'answer': 'Hash tables provide O(1) average time complexity for insertions and lookups.'
        }
    ]
    return questions

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/features')
def features():
    """Features page"""
    return render_template('features.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page and user creation"""
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        # Hash the password
        password_hash = generate_password_hash(password)
        
        try:
            conn = sqlite3.connect('interview_prep.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                         (name, email, password_hash))
            conn.commit()
            conn.close()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('interview_prep.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, password_hash FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """User dashboard - requires authentication"""
    if 'user_id' not in session:
        flash('Please login to access dashboard', 'error')
        return redirect(url_for('login'))
    
    # Get user statistics
    conn = sqlite3.connect('interview_prep.db')
    cursor = conn.cursor()
    
    # Total questions attempted
    cursor.execute('SELECT COUNT(*) FROM attempts WHERE user_id = ?', (session['user_id'],))
    total_attempted = cursor.fetchone()[0]
    
    # Correct answers
    cursor.execute('SELECT COUNT(*) FROM attempts WHERE user_id = ? AND correct = 1', (session['user_id'],))
    correct_answers = cursor.fetchone()[0]
    
    # Total mock interviews taken
    cursor.execute('SELECT COUNT(*) FROM mock_sessions WHERE user_id = ?', (session['user_id'],))
    total_interviews = cursor.fetchone()[0]
    
    # Recent mock interview performance
    cursor.execute('''
        SELECT total_questions, correct_answers, start_time 
        FROM mock_sessions 
        WHERE user_id = ? AND total_questions > 0
        ORDER BY start_time DESC 
        LIMIT 5
    ''', (session['user_id'],))
    recent_interviews = cursor.fetchall()
    
    # Calculate total study time (approximate based on attempts)
    total_study_time = total_attempted * 5  # Assume 5 minutes per question
    
    # Get weak topics (questions with most incorrect answers)
    cursor.execute('''
        SELECT question_id, COUNT(*) as incorrect_count
        FROM attempts 
        WHERE user_id = ? AND correct = 0
        GROUP BY question_id 
        ORDER BY incorrect_count DESC 
        LIMIT 3
    ''', (session['user_id'],))
    weak_topics = cursor.fetchall()
    
    conn.close()
    
    # Calculate accuracy
    accuracy = (correct_answers / total_attempted * 100) if total_attempted > 0 else 0
    
    # Calculate day streak (simplified)
    day_streak = min(total_attempted // 5, 30)  # Assume 5 questions per day, max 30 days
    
    stats = {
        'total_attempted': total_attempted,
        'correct_answers': correct_answers,
        'accuracy': round(accuracy, 1),
        'total_interviews': total_interviews,
        'recent_interviews': recent_interviews,
        'total_study_time': total_study_time,
        'weak_topics': weak_topics,
        'day_streak': day_streak
    }
    
    return render_template('dashboard.html', stats=stats)

@app.route('/practice')
def practice():
    """Practice questions page"""
    if 'user_id' not in session:
        flash('Please login to access practice questions', 'error')
        return redirect(url_for('login'))
    return render_template('practice.html')

@app.route('/dsa')
def dsa():
    """DSA Practice mode - alternative route for the More menu"""
    if 'user_id' not in session:
        flash('Please login to access DSA practice', 'error')
        return redirect(url_for('login'))
    
    return render_template('practice.html')

@app.route('/resources')
def resources():
    """Resources page"""
    return render_template('resources.html')

@app.route('/career_roadmap')
def career_roadmap():
    """Career Roadmap Generator page"""
    return render_template('career_roadmap.html')

@app.route('/mock')
def mock_interview():
    """Start mock interview session"""
    if 'user_id' not in session:
        flash('Please login to access mock interview', 'error')
        return redirect(url_for('login'))
    
    # Create new mock session
    conn = sqlite3.connect('interview_prep.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO mock_sessions (user_id) VALUES (?)
    ''', (session['user_id'],))
    mock_session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    session['mock_session_id'] = mock_session_id
    session['mock_start_time'] = datetime.now().isoformat()
    session['mock_questions_answered'] = 0
    
    return render_template('mock_interview.html', session_id=mock_session_id)

@app.route('/submit-answer', methods=['POST'])
def submit_answer():
    """Submit answer for a question"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    question_id = data.get('question_id')
    correct = data.get('correct', False)
    user_answer = data.get('user_answer', '')
    
    # Save attempt to database
    conn = sqlite3.connect('interview_prep.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO attempts (user_id, question_id, correct, user_answer)
        VALUES (?, ?, ?, ?)
    ''', (session['user_id'], question_id, correct, user_answer))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Answer submitted successfully'})

@app.route('/api/stats')
def api_stats():
    """API endpoint to get user statistics"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = sqlite3.connect('interview_prep.db')
    cursor = conn.cursor()
    
    # Total questions attempted
    cursor.execute('SELECT COUNT(*) FROM attempts WHERE user_id = ?', (session['user_id'],))
    total_attempted = cursor.fetchone()[0]
    
    # Correct answers
    cursor.execute('SELECT COUNT(*) FROM attempts WHERE user_id = ? AND correct = 1', (session['user_id'],))
    correct_answers = cursor.fetchone()[0]
    
    conn.close()
    
    # Calculate accuracy
    accuracy = (correct_answers / total_attempted * 100) if total_attempted > 0 else 0
    
    return jsonify({
        'total_attempted': total_attempted,
        'correct_answers': correct_answers,
        'accuracy': round(accuracy, 1),
        'weak_topics': []  # Will be populated later
    })

if __name__ == '__main__':
    # Use environment variable for port, default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # In production, don't use debug mode
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)

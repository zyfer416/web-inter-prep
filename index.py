from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random

# Create Flask app
app = Flask(__name__, 
           template_folder="frontend/templates", 
           static_folder="frontend/static")
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Configure for production
app.config['DEBUG'] = False

# Database initialization
def init_db():
    """Initialize the SQLite database with required tables"""
    # Use a persistent path for Render
    db_path = os.path.join(os.path.expanduser('~'), 'interview_prep.db')
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

# Initialize database
init_db()

# Routes
@app.route('/')
def home():
    """Home page route"""
    return render_template('home.html')

@app.route('/features')
def features():
    """Features showcase page"""
    return render_template('features.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db_path = os.path.join(os.path.expanduser('~'), 'interview_prep.db')
        conn = sqlite3.connect(db_path)
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
            db_path = os.path.join(os.path.dirname(__file__), 'interview_prep.db')
            conn = sqlite3.connect(db_path)
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

@app.route('/dashboard')
def dashboard():
    """User dashboard - requires authentication"""
    if 'user_id' not in session:
        flash('Please login to access dashboard', 'error')
        return redirect(url_for('login'))
    
    # Get user statistics
    db_path = os.path.join(os.path.expanduser('~'), 'interview_prep.db')
    conn = sqlite3.connect(db_path)
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
    
    conn.close()
    
    # Calculate accuracy
    accuracy = (correct_answers / total_attempted * 100) if total_attempted > 0 else 0
    
    stats = {
        'total_attempted': total_attempted,
        'correct_answers': correct_answers,
        'accuracy': round(accuracy, 1),
        'total_interviews': total_interviews,
        'current_streak': 0,
        'weak_topics': [],
        'recent_interviews': []
    }
    
    return render_template('dashboard.html', stats=stats)

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

@app.route('/practice')
def practice_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("practice.html")

@app.route('/resume')
def resume():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("resume.html")

@app.route('/mock')
def mock_interview():
    """Start mock interview session"""
    if 'user_id' not in session:
        flash('Please login to access mock interview', 'error')
        return redirect(url_for('login'))
    
    # Create new mock session
    db_path = os.path.join(os.path.dirname(__file__), 'interview_prep.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO mock_sessions (user_id) VALUES (?)', (session['user_id'],))
    mock_session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    session['mock_session_id'] = mock_session_id
    session['mock_start_time'] = datetime.now().isoformat()
    session['mock_questions_answered'] = 0
    
    return render_template('mock_interview.html', session_id=mock_session_id)

@app.route('/resources')
def resources():
    """Learning resources page"""
    resources_data = {
        'technical': [
            {
                'title': 'LeetCode',
                'description': 'Practice coding problems and algorithms',
                'url': 'https://leetcode.com',
                'type': 'Practice Platform'
            }
        ],
        'behavioral': [
            {
                'title': 'STAR Method Guide',
                'description': 'Structure your behavioral interview answers',
                'url': 'https://www.indeed.com/career-advice/interviewing/how-to-use-the-star-interview-response-technique',
                'type': 'Article'
            }
        ],
        'general': [
            {
                'title': 'Interview Tips and Strategies',
                'description': 'General advice for interview success',
                'url': 'https://www.indeed.com/career-advice/interviewing',
                'type': 'Resource Hub'
            }
        ]
    }
    
    return render_template('resources.html', resources=resources_data)

@app.route('/career_roadmap')
def career_roadmap():
    """Career Roadmap Generator page"""
    return render_template('career_roadmap.html')

@app.route('/ai-interview')
def ai_interview():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('ai_interview.html')

@app.route('/calendar')
def calendar():
    """Interview calendar page"""
    if 'user_id' not in session:
        flash('Please login to access calendar', 'error')
        return redirect(url_for('login'))
    return render_template('calendar.html')

@app.route('/custom')
def custom_practice():
    """Custom practice session"""
    if 'user_id' not in session:
        flash('Please login to access custom practice', 'error')
        return redirect(url_for('login'))
    
    return render_template('custom_practice.html')

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('errors/500.html'), 500

# For Render deployment
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

"""
Web-Inter-Prep - Online Interview Preparation Platform
Main Flask Application File
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # Change this in production

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

@app.route('/')
def home():
    """Home page route"""
    return render_template('home.html')

@app.route('/features')
def features():
    """Features showcase page"""
    return render_template('features.html')

@app.route('/career_roadmap')
def career_roadmap():
    """Career Roadmap Generator page"""
    return render_template('career_roadmap.html')

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
    weak_topics_data = cursor.fetchall()
    
    # Load questions to get topic names
    questions = load_questions()
    questions_dict = {q['id']: q for q in questions}
    
    weak_topics = []
    for topic_id, count in weak_topics_data:
        if topic_id in questions_dict:
            weak_topics.append({
                'name': questions_dict[topic_id].get('category', 'Unknown'),
                'count': count
            })
    
    # Calculate accuracy
    accuracy = (correct_answers / total_attempted * 100) if total_attempted > 0 else 0
    
    # Calculate score out of 10
    score_out_of_10 = round((accuracy / 100) * 10, 1)
    
    # Get streak information (consecutive days with practice)
    cursor.execute('''
        SELECT DATE(timestamp) as practice_date
        FROM attempts 
        WHERE user_id = ?
        GROUP BY DATE(timestamp)
        ORDER BY practice_date DESC
    ''', (session['user_id'],))
    practice_dates = [row[0] for row in cursor.fetchall()]
    
    # Calculate current streak
    current_streak = 0
    if practice_dates:
        from datetime import date, timedelta
        today = date.today()
        current_date = today
        
        for practice_date in practice_dates:
            practice_date_obj = datetime.strptime(practice_date, '%Y-%m-%d').date()
            if current_date == practice_date_obj:
                current_streak += 1
                current_date -= timedelta(days=1)
            else:
                break
    
    conn.close()
    
    stats = {
        'total_attempted': total_attempted,
        'correct_answers': correct_answers,
        'accuracy': round(accuracy, 1),
        'score_out_of_10': score_out_of_10,
        'total_interviews': total_interviews,
        'total_study_time': total_study_time,
        'current_streak': current_streak,
        'weak_topics': weak_topics,
        'recent_interviews': recent_interviews
    }
    
    return render_template('dashboard.html', stats=stats)

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

def load_questions():
    """Load questions from JSON file"""
    try:
        with open('data/questions.json', 'r') as f:
            data = json.load(f)
            return data['questions']
    except FileNotFoundError:
        return []

@app.route('/practice')
def practice():
    """DSA Practice mode - show categories and practice questions"""
    if 'user_id' not in session:
        flash('Please login to access practice mode', 'error')
        return redirect(url_for('login'))
    
    return render_template('practice.html')

@app.route('/dsa')
def dsa():
    """DSA Practice mode - alternative route for the More menu"""
    if 'user_id' not in session:
        flash('Please login to access DSA practice', 'error')
        return redirect(url_for('login'))
    
    return render_template('practice.html')

# Old practice API endpoint removed - now using client-side DSA questions

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

@app.route('/mock/question')
def mock_question():
    """Get next question for mock interview"""
    if 'user_id' not in session or 'mock_session_id' not in session:
        return jsonify({'error': 'No active mock session'}), 400
    
    questions = load_questions()
    if not questions:
        return jsonify({'error': 'No questions available'}), 404
    
    # Select a random question
    question = random.choice(questions)
    return jsonify({'question': question})

@app.route('/mock/submit', methods=['POST'])
def mock_submit_answer():
    """Submit answer during mock interview"""
    if 'user_id' not in session or 'mock_session_id' not in session:
        return jsonify({'error': 'No active mock session'}), 400
    
    data = request.get_json()
    question_id = data.get('question_id')
    user_answer = data.get('user_answer', '')
    time_taken = data.get('time_taken', 0)
    
    # For simplicity, we'll mark as correct if user provided an answer
    correct = len(user_answer.strip()) > 10  # Basic check for substantial answer
    
    # Save attempt
    conn = sqlite3.connect('interview_prep.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO attempts (user_id, question_id, correct, user_answer)
        VALUES (?, ?, ?, ?)
    ''', (session['user_id'], question_id, correct, user_answer))
    conn.commit()
    conn.close()
    
    # Update session counter
    session['mock_questions_answered'] = session.get('mock_questions_answered', 0) + 1
    
    return jsonify({
        'success': True, 
        'correct': correct,
        'questions_answered': session['mock_questions_answered']
    })

@app.route('/mock/end', methods=['POST'])
def end_mock_interview():
    """End mock interview session"""
    if 'user_id' not in session or 'mock_session_id' not in session:
        return jsonify({'error': 'No active mock session'}), 400
    
    mock_session_id = session['mock_session_id']
    questions_answered = session.get('mock_questions_answered', 0)
    
    # Get statistics for this session
    conn = sqlite3.connect('interview_prep.db')
    cursor = conn.cursor()
    
    # Count correct answers from this session (approximate by recent attempts)
    cursor.execute('''
        SELECT COUNT(*) FROM attempts 
        WHERE user_id = ? AND correct = 1 
        AND timestamp >= datetime('now', '-30 minutes')
    ''', (session['user_id'],))
    correct_answers = cursor.fetchone()[0]
    
    # Update mock session
    cursor.execute('''
        UPDATE mock_sessions 
        SET end_time = CURRENT_TIMESTAMP, total_questions = ?, correct_answers = ?
        WHERE id = ?
    ''', (questions_answered, correct_answers, mock_session_id))
    conn.commit()
    conn.close()
    
    # Clear session variables
    session.pop('mock_session_id', None)
    session.pop('mock_start_time', None)
    session.pop('mock_questions_answered', None)
    
    return jsonify({
        'success': True,
        'total_questions': questions_answered,
        'correct_answers': correct_answers,
        'score': round((correct_answers / questions_answered * 100) if questions_answered > 0 else 0, 1)
    })

@app.route('/mock/results')
def mock_results():
    """Show mock interview results"""
    if 'user_id' not in session:
        flash('Please login to view results', 'error')
        return redirect(url_for('login'))
    
    # Get latest mock session
    conn = sqlite3.connect('interview_prep.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT total_questions, correct_answers, start_time, end_time
        FROM mock_sessions 
        WHERE user_id = ? 
        ORDER BY start_time DESC LIMIT 1
    ''', (session['user_id'],))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        flash('No mock interview session found', 'error')
        return redirect(url_for('dashboard'))
    
    total_questions, correct_answers, start_time, end_time = result
    score = round((correct_answers / total_questions * 100) if total_questions > 0 else 0, 1)
    
    # Calculate duration
    if end_time:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        duration = str(end_dt - start_dt).split('.')[0]  # Remove microseconds
    else:
        duration = "Unknown"
    
    results = {
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'score': score,
        'duration': duration
    }
    
    return render_template('mock_results.html', results=results)

@app.route('/feedback')
def feedback():
    """Show detailed feedback for user attempts"""
    if 'user_id' not in session:
        flash('Please login to view feedback', 'error')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('interview_prep.db')
    cursor = conn.cursor()
    
    # Get recent attempts with question details
    cursor.execute('''
        SELECT a.id, a.question_id, a.correct, a.user_answer, a.timestamp
        FROM attempts a
        WHERE a.user_id = ?
        ORDER BY a.timestamp DESC
        LIMIT 20
    ''', (session['user_id'],))
    attempts = cursor.fetchall()
    conn.close()
    
    # Load questions to get details
    questions = load_questions()
    questions_dict = {q['id']: q for q in questions}
    
    # Combine attempts with question details
    feedback_data = []
    for attempt in attempts:
        attempt_id, question_id, correct, user_answer, timestamp = attempt
        if question_id in questions_dict:
            question = questions_dict[question_id]
            feedback_data.append({
                'attempt_id': attempt_id,
                'question': question,
                'correct': correct,
                'user_answer': user_answer,
                'timestamp': timestamp
            })
    
    return render_template('feedback.html', feedback_data=feedback_data)

@app.route('/resources')
def resources():
    """Learning resources page"""
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
            },
            {
                'title': 'System Design Primer',
                'description': 'Learn system design concepts and patterns',
                'url': 'https://github.com/donnemartin/system-design-primer',
                'type': 'GitHub Repository'
            }
        ],
        'behavioral': [
            {
                'title': 'STAR Method Guide',
                'description': 'Structure your behavioral interview answers',
                'url': 'https://www.indeed.com/career-advice/interviewing/how-to-use-the-star-interview-response-technique',
                'type': 'Article'
            },
            {
                'title': 'Common Behavioral Questions',
                'description': 'Prepare for typical behavioral interview questions',
                'url': 'https://www.glassdoor.com/blog/behavioral-interview-questions/',
                'type': 'Article'
            }
        ],
        'general': [
            {
                'title': 'Interview Tips and Strategies',
                'description': 'General advice for interview success',
                'url': 'https://www.indeed.com/career-advice/interviewing',
                'type': 'Resource Hub'
            },
            {
                'title': 'Salary Negotiation Guide',
                'description': 'Learn how to negotiate your offer',
                'url': 'https://www.kalzumeus.com/2012/01/23/salary-negotiation/',
                'type': 'Article'
            }
        ]
    }
    
    return render_template('resources.html', resources=resources_data)

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8081)

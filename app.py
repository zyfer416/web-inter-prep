from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import requests
import sqlite3
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random

# Load environment once
load_dotenv()

# Create Flask app with correct paths
app = Flask(__name__, 
           template_folder="frontend/templates", 
           static_folder="frontend/static")
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Configure for production
app.config['DEBUG'] = False

# OAuth configuration (Google)
oauth = OAuth(app)
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')

# Register Google OAuth if credentials are available
if app.config['GOOGLE_CLIENT_ID'] and app.config['GOOGLE_CLIENT_SECRET']:
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

# Helper function to get database path
def get_db_path():
    """Get the appropriate database path based on environment"""
    if os.environ.get('RENDER'):
        # Production environment (Render)
        return os.path.join(os.path.expanduser('~'), 'interview_prep.db')
    else:
        # Development environment
        return os.path.join(os.path.dirname(__file__), 'interview_prep.db')

# Database initialization
def init_db():
    """Initialize the SQLite database with required tables"""
    db_path = get_db_path()
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
try:
    init_db()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"⚠️  Database initialization warning: {e}")

# --- AI Interviewer: Gemini helper and routes ---

def _gemini_call(parts, expect_json=False, temperature=0.6):
    """Call Gemini generateContent with given parts. Returns text."""
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY not configured, using fallback responses")
        return ""
    
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": temperature}
    }
    if expect_json:
        payload["generationConfig"]["response_mime_type"] = "application/json"

    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=30
    )
    if resp.status_code != 200:
        print(f"Gemini API error: {resp.status_code} - {resp.text}")
        return ""
    
    try:
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        print(f"Gemini response parsing error: {e}")
        return ""

def ask_gemini(prompt, expect_json=False, temperature=0.6):
    """Ask Gemini a question and return the response."""
    parts = [{"text": prompt}]
    return _gemini_call(parts, expect_json=expect_json, temperature=temperature)

# Load questions from JSON file
def load_questions():
    """Load questions from JSON file"""
    try:
        with open('backend/data/questions.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback questions if file doesn't exist
        return {
            "technical": [
                {
                    "question": "What is the difference between a list and a tuple in Python?",
                    "options": ["Lists are mutable, tuples are immutable", "Tuples are mutable, lists are immutable", "No difference", "Lists are faster"],
                    "correct": 0,
                    "explanation": "Lists are mutable (can be modified) while tuples are immutable (cannot be modified after creation)."
                }
            ],
            "behavioral": [
                {
                    "question": "Tell me about a time you had to work under pressure.",
                    "options": ["I avoid pressure", "I work well under pressure", "I get stressed easily", "I delegate under pressure"],
                    "correct": 1,
                    "explanation": "This is a common behavioral interview question to assess how you handle challenging situations."
                }
            ]
        }

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
        
        try:
            # Use consistent database path
            db_path = get_db_path()
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
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page and user creation"""
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        # Basic validation
        if not name or not email or not password:
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        # Hash the password
        password_hash = generate_password_hash(password)
        
        try:
            db_path = get_db_path()
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
        except Exception as e:
            flash(f'Registration error: {str(e)}', 'error')
    
    return render_template('register.html')

# Google OAuth routes
@app.route('/login/google')
def google_login():
    """Google OAuth login"""
    if not app.config['GOOGLE_CLIENT_ID']:
        flash('Google login not configured', 'error')
        return redirect(url_for('login'))
    
    redirect_uri = url_for('google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def google_callback():
    """Google OAuth callback"""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if user_info:
            email = user_info.get('email')
            name = user_info.get('name', '')
            
            # Check if user exists, if not create them
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, name FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if not user:
                # Create new user with Google OAuth
                cursor.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                               (name, email, 'oauth_user'))
                user_id = cursor.lastrowid
                conn.commit()
            else:
                user_id = user[0]
                name = user[1]
            
            conn.close()
            
            # Set session
            session['user_id'] = user_id
            session['user_name'] = name
            flash('Google login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Google login failed', 'error')
            return redirect(url_for('login'))
    except Exception as e:
        flash(f'Google login error: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """User dashboard - requires authentication"""
    if 'user_id' not in session:
        flash('Please login to access dashboard', 'error')
        return redirect(url_for('login'))
    
    try:
        # Get user statistics
        db_path = get_db_path()
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
    except Exception as e:
        flash(f'Dashboard error: {str(e)}', 'error')
        return render_template('dashboard.html', stats={
            'total_attempted': 0,
            'correct_answers': 0,
            'accuracy': 0,
            'total_interviews': 0,
            'current_streak': 0,
            'weak_topics': [],
            'recent_interviews': []
        })

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

@app.route('/practice')
def practice():
    """Practice questions page"""
    if 'user_id' not in session:
        flash('Please login to access practice', 'error')
        return redirect(url_for('login'))
    
    questions_data = load_questions()
    return render_template('practice.html', questions=questions_data)

@app.route('/mock-interview')
def mock_interview():
    """Start mock interview session"""
    if 'user_id' not in session:
        flash('Please login to access mock interview', 'error')
        return redirect(url_for('login'))
    
    # Create new mock session
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO mock_sessions (user_id) VALUES (?)', (session['user_id'],))
    mock_session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    session['mock_session_id'] = mock_session_id
    return render_template('mock_interview.html')

@app.route('/ai-interview')
def ai_interview():
    """AI-powered interview with Gemini"""
    if 'user_id' not in session:
        flash('Please login to access AI interview', 'error')
        return redirect(url_for('login'))
    
    return render_template('ai_interview.html')

@app.route('/ai-interview/start', methods=['POST'])
def start_ai_interview():
    """Start AI interview session"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get interview parameters
        data = request.get_json()
        role = data.get('role', 'Software Engineer')
        difficulty = data.get('difficulty', 'intermediate')
        
        # Generate interview questions using Gemini
        prompt = f"""
        Generate 5 interview questions for a {role} position at {difficulty} level.
        Include both technical and behavioral questions.
        Return as JSON with this structure:
        {{
            "questions": [
                {{
                    "question": "Question text",
                    "type": "technical" or "behavioral",
                    "expected_answer": "Brief expected answer"
                }}
            ]
        }}
        """
        
        response = ask_gemini(prompt, expect_json=True)
        
        if response:
            try:
                questions_data = json.loads(response)
                session['ai_interview_questions'] = questions_data
                session['ai_interview_current'] = 0
                return jsonify({'success': True, 'questions': questions_data})
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                questions_data = {
                    "questions": [
                        {
                            "question": f"Tell me about your experience with {role}.",
                            "type": "behavioral",
                            "expected_answer": "Share relevant experience and achievements."
                        }
                    ]
                }
                session['ai_interview_questions'] = questions_data
                session['ai_interview_current'] = 0
                return jsonify({'success': True, 'questions': questions_data})
        else:
            return jsonify({'error': 'Failed to generate questions'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ai-interview/answer', methods=['POST'])
def submit_ai_answer():
    """Submit answer for AI interview question"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        answer = data.get('answer', '')
        current_question = session.get('ai_interview_current', 0)
        questions = session.get('ai_interview_questions', {}).get('questions', [])
        
        if current_question >= len(questions):
            return jsonify({'error': 'No more questions'}), 400
        
        # Get AI feedback using Gemini
        question = questions[current_question]
        feedback_prompt = f"""
        Question: {question['question']}
        User Answer: {answer}
        Expected Answer: {question.get('expected_answer', 'N/A')}
        
        Provide constructive feedback on this answer. Be encouraging but honest.
        Return as JSON:
        {{
            "feedback": "Your feedback here",
            "score": 1-10,
            "suggestions": ["suggestion1", "suggestion2"]
        }}
        """
        
        feedback_response = ask_gemini(feedback_prompt, expect_json=True)
        
        if feedback_response:
            try:
                feedback_data = json.loads(feedback_response)
                session['ai_interview_current'] = current_question + 1
                
                return jsonify({
                    'success': True,
                    'feedback': feedback_data,
                    'next_question': questions[current_question + 1] if current_question + 1 < len(questions) else None
                })
            except json.JSONDecodeError:
                return jsonify({
                    'success': True,
                    'feedback': {
                        'feedback': 'Good answer! Keep going.',
                        'score': 7,
                        'suggestions': ['Continue with confidence']
                    },
                    'next_question': questions[current_question + 1] if current_question + 1 < len(questions) else None
                })
        else:
            return jsonify({'error': 'Failed to get feedback'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/resources')
def resources():
    """Resources page"""
    return render_template('resources.html')

@app.route('/resume')
def resume():
    """Resume builder page"""
    if 'user_id' not in session:
        flash('Please login to access resume builder', 'error')
        return redirect(url_for('login'))
    
    return render_template('resume.html')

@app.route('/career-roadmap')
def career_roadmap():
    """Career roadmap page"""
    if 'user_id' not in session:
        flash('Please login to access career roadmap', 'error')
        return redirect(url_for('login'))
    
    return render_template('career_roadmap.html')

@app.route('/company-prep')
def company_prep():
    """Company-specific preparation page"""
    if 'user_id' not in session:
        flash('Please login to access company prep', 'error')
        return redirect(url_for('login'))
    
    return render_template('company_prep.html')

@app.route('/feedback')
def feedback():
    """Feedback page"""
    return render_template('feedback.html')

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

# WSGI application for production
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

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

app = Flask(__name__, template_folder="frontend/templates", static_folder="frontend/static")
app.secret_key = 'your-secret-key-change-in-production'  # Change this in production

# OAuth configuration (Google)
oauth = OAuth(app)
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')  # configurable model

if app.config['GOOGLE_CLIENT_ID'] and app.config['GOOGLE_CLIENT_SECRET']:
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
    

# Database initialization
def init_db():
    """Initialize the SQLite database with required tables"""
    db_path = os.path.join(os.path.dirname(__file__), 'interview_prep.db')
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

# Initialize database on startup
init_db()

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
        # Ask Gemini to return JSON text; route still parses it on our side
        payload["generationConfig"]["response_mime_type"] = "application/json"

    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        headers={"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY},
        json=payload, timeout=20
    )
    if resp.status_code != 200:
        # Return truncated body for UI error handling
        return ""
    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    parts = (candidates[0].get("content") or {}).get("parts", [])
    text = "\n".join([p.get("text", "") for p in parts if p.get("text")]).strip()
    return text

@app.route("/api/ai-interview/start", methods=["POST"])
def ai_interview_start():
    """Start an AI interview: creates mock_session, returns first question."""
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "Not authenticated"}), 401

    body = request.get_json(force=True, silent=True) or {}
    role = (body.get("role") or "Software Engineer").strip()
    level = (body.get("level") or "Fresher").strip()
    company = (body.get("company") or "Any").strip()
    topic = (body.get("topic") or "technical").strip()
    question_count = body.get("questionCount", 5)
    time_limit = body.get("timeLimit", 30)

    # Create a mock session row (reuse your schema)
    conn = sqlite3.connect("interview_prep.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO mock_sessions (user_id) VALUES (?)", (session["user_id"],))
    mock_session_id = cur.lastrowid
    conn.commit()
    conn.close()

    session["mock_session_id"] = mock_session_id
    session["ai_round"] = 1
    session["ai_question_count"] = question_count
    session["ai_time_limit"] = time_limit
    session["ai_topic"] = topic

    # Generate topic-specific prompt
    topic_prompts = {
        "technical": "Ask a technical programming question",
        "behavioral": "Ask a behavioral/situational question", 
        "system-design": "Ask a system design question",
        "mixed": "Ask either a technical or behavioral question"
    }
    
    topic_instruction = topic_prompts.get(topic, "Ask a technical question")

    interviewer_prompt = (
        f"You are an interviewer for role '{role}' at '{company}' for a '{level}' candidate. "
        f"{topic_instruction}. Ask one concise question only. No preface, no explanation. "
        "Return strict JSON with keys: question, topic."
    )
    txt = _gemini_call([{"text": interviewer_prompt}], expect_json=True)
    try:
        qobj = json.loads(txt) if txt else {}
    except Exception:
        qobj = {}
    
    # Fallback questions if Gemini fails
    if not qobj.get("question"):
        fallback_questions = {
            "technical": [
                {"question": "Explain the difference between REST and GraphQL APIs.", "topic": "Technical"},
                {"question": "How would you design a URL shortening service like bit.ly?", "topic": "System Design"},
                {"question": "What is the difference between SQL and NoSQL databases?", "topic": "Technical"}
            ],
            "behavioral": [
                {"question": "Tell me about a time when you had to work with a difficult team member.", "topic": "Behavioral"},
                {"question": "Describe a project where you had to learn a new technology quickly.", "topic": "Behavioral"},
                {"question": "Give me an example of a time when you had to make a difficult technical decision.", "topic": "Behavioral"}
            ],
            "system-design": [
                {"question": "Design a chat application that can handle millions of users.", "topic": "System Design"},
                {"question": "How would you design a recommendation system for an e-commerce platform?", "topic": "System Design"},
                {"question": "Design a distributed file storage system.", "topic": "System Design"}
            ]
        }
        import random
        topic_questions = fallback_questions.get(topic, fallback_questions["technical"])
        qobj = random.choice(topic_questions)

    return jsonify({
        "ok": True,
        "session_id": mock_session_id,
        "question": qobj.get("question", ""),
        "topic": qobj.get("topic", "General")
    })

@app.route("/api/ai-interview/answer", methods=["POST"])
def ai_interview_answer():
    """Grade the answer and return feedback + next question."""
    if "user_id" not in session or "mock_session_id" not in session:
        return jsonify({"ok": False, "error": "No active interview"}), 400

    body = request.get_json(force=True, silent=True) or {}
    question_text = (body.get("question") or "").strip()
    user_answer = (body.get("answer") or "").strip()
    if not question_text or not user_answer:
        return jsonify({"ok": False, "error": "Missing question or answer"}), 400

    # Evaluator rubric prompt - 10 point scale
    rubric = (
        "Evaluate the candidate's answer on a 10-point scale. "
        "Score 10: Excellent answer with all key points covered, clear explanation, good examples. "
        "Score 8-9: Good answer with most key points, clear structure. "
        "Score 6-7: Adequate answer with some key points, basic understanding. "
        "Score 4-5: Poor answer with few key points, unclear explanation. "
        "Score 0-3: Very poor answer with major gaps or incorrect information. "
        "Also provide: correctness (0-3), clarity (0-3), depth (0-2), conciseness (0-2). "
        "verdict in [Pass, Borderline, Improve]. "
        "Provide strengths (3 items), improvements (3 items), ideal_answer (5-8 lines). "
        "Return strict JSON with keys: correctness, clarity, depth, conciseness, score_10, verdict, strengths, improvements, ideal_answer."
    )
    eval_prompt = f"Question:\n{question_text}\n\nCandidate_Answer:\n{user_answer}\n\n{rubric}"
    eval_json_text = _gemini_call([{"text": eval_prompt}], expect_json=True, temperature=0.2)

    try:
        evaluation = json.loads(eval_json_text) if eval_json_text else {}
    except Exception:
        evaluation = {}

    # Reasonable fallback if model didn't return JSON or no API key
    if not isinstance(evaluation, dict) or "score_10" not in evaluation:
        # Simple scoring based on answer length and content
        answer_length = len(user_answer.strip())
        if answer_length < 20:
            score = 3
            verdict = "Improve"
        elif answer_length < 50:
            score = 5
            verdict = "Borderline"
        elif answer_length < 100:
            score = 7
            verdict = "Pass"
        else:
            score = 8
            verdict = "Pass"
        
        evaluation = {
            "correctness": min(3, score // 3), 
            "clarity": min(3, score // 3), 
            "depth": min(2, score // 4), 
            "conciseness": min(2, score // 4),
            "score_10": score, 
            "verdict": verdict,
            "strengths": ["Provided an answer", "Showed understanding"], 
            "improvements": ["Add more detail", "Provide examples"], 
            "ideal_answer": "A comprehensive answer with clear structure, examples, and technical details."
        }

    # Save attempt with feedback JSON stuffed in user_answer
    try:
        conn = sqlite3.connect("interview_prep.db")
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO attempts (user_id, question_id, correct, user_answer, mock_session_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (session["user_id"], 0, 1 if int(evaluation.get("score_10", 0)) >= 7 else 0,
              json.dumps({"q": question_text, "a": user_answer, "feedback": evaluation}),
              session["mock_session_id"]))
        conn.commit()
    finally:
        conn.close()

    # Check if we should continue with more questions
    current_round = int(session.get("ai_round", 1))
    question_count = int(session.get("ai_question_count", 5))
    
    if current_round >= question_count:
        # Interview complete
        return jsonify({
            "ok": True,
            "evaluation": evaluation,
            "interview_complete": True,
            "final_score": evaluation.get("score_10", 0),
            "total_questions": current_round
        })
    
    # Next question
    session["ai_round"] = current_round + 1
    topic = session.get("ai_topic", "technical")
    
    # Generate topic-specific next question
    topic_prompts = {
        "technical": "Ask a technical programming question",
        "behavioral": "Ask a behavioral/situational question", 
        "system-design": "Ask a system design question",
        "mixed": "Ask either a technical or behavioral question"
    }
    
    topic_instruction = topic_prompts.get(topic, "Ask a technical question")
    
    next_prompt = (
        f"Based on the previous question and the candidate's answer quality, ask the next interview question. "
        f"{topic_instruction}. Increase difficulty gradually. Return strict JSON: {{\"question\":\"...\",\"topic\":\"...\"}}. "
        f"Previous question: {question_text}"
    )
    next_json_text = _gemini_call([{"text": next_prompt}], expect_json=True)
    try:
        nxt = json.loads(next_json_text) if next_json_text else {}
    except Exception:
        nxt = {}
    
    # Fallback next question if Gemini fails
    if not nxt.get("question"):
        fallback_questions = {
            "technical": [
                {"question": "Explain the concept of database indexing and how it improves query performance.", "topic": "Technical"},
                {"question": "What is the difference between synchronous and asynchronous programming?", "topic": "Technical"},
                {"question": "How would you implement a hash table from scratch?", "topic": "Technical"}
            ],
            "behavioral": [
                {"question": "Tell me about a time when you had to debug a complex issue.", "topic": "Behavioral"},
                {"question": "Describe a situation where you had to work under pressure.", "topic": "Behavioral"},
                {"question": "How do you stay updated with the latest technology trends?", "topic": "Behavioral"}
            ],
            "system-design": [
                {"question": "How would you design a social media feed system?", "topic": "System Design"},
                {"question": "Design a load balancer that can handle traffic spikes.", "topic": "System Design"},
                {"question": "How would you design a real-time analytics system?", "topic": "System Design"}
            ]
        }
        import random
        topic_questions = fallback_questions.get(topic, fallback_questions["technical"])
        nxt = random.choice(topic_questions)

    return jsonify({
        "ok": True,
        "evaluation": evaluation,
        "next_question": nxt.get("question", ""),
        "next_topic": nxt.get("topic", "General"),
        "round": session["ai_round"]
    })

@app.route("/api/gemini/solve", methods=["POST"])
def gemini_solve():
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "Not authenticated"}), 401
    data = request.get_json(force=True, silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    topics = data.get("topics") or []
    language = (data.get("language") or "Python").strip()

    if not GEMINI_API_KEY:
        return jsonify({"ok": False, "error": "GEMINI_API_KEY not configured"}), 500
    if not title:
        return jsonify({"ok": False, "error": "Missing title"}), 400

    # Ask for strict JSON so parsing is predictable
    prompt = (
        "You are an expert DSA tutor. Given a LeetCode-style problem, produce a concise, interview-ready solution.\n"
        f"Title: {title}\n"
        f"Description: {description}\n"
        f"Topics: {', '.join(topics)}\n"
        f"Language: {language}\n\n"
        "Return strict JSON with keys:\n"
        "approach (1-3 sentences), timeComplexity (e.g., O(n log n)), spaceComplexity, "
        "code (complete runnable snippet), explanation (3-6 sentences).\n"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "response_mime_type": "application/json"
        }
    }

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            headers={"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY},
            json=payload, timeout=20
        )
        if resp.status_code != 200:
            return jsonify({"ok": False, "error": f"Gemini error {resp.status_code}: {resp.text[:300]}"}), 502
        data = resp.json()
        parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
        text = "\n".join([p.get("text","") for p in parts if p.get("text")]).strip()
        try:
            result = json.loads(text) if text else {}
        except Exception:
            result = {}
        # minimal validation/fallback
        result.setdefault("approach", "High-level idea not available.")
        result.setdefault("timeComplexity", "Unknown")
        result.setdefault("spaceComplexity", "Unknown")
        result.setdefault("code", "# Code unavailable")
        result.setdefault("explanation", "Explanation unavailable.")
        return jsonify({"ok": True, "solution": result})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Unexpected error: {e}"}), 500

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

@app.route('/api/roadmap', methods=['POST'])
def api_roadmap():
    """Generate a career roadmap using Gemini API.
    Expects JSON: { jobRole, experience, targetCompany, skills }
    Returns: { html }
    """
    data = request.get_json(force=True, silent=True) or {}
    job_role = data.get('jobRole', '')
    experience = data.get('experience', '')
    target_company = data.get('targetCompany', '')
    skills = data.get('skills', '')

    if not GEMINI_API_KEY:
        return jsonify({'error': 'GEMINI_API_KEY not configured on server'}), 500

    prompt = (
        f"Create a concise, step-by-step career roadmap for role: {job_role}, "
        f"experience: {experience}, target company: {target_company}. "
        f"Candidate skills: {skills}. "
        "Return three stages (Foundational, Intermediate, Advanced). For each stage, provide: "
        "Key Milestones (3-5 bullets), Skills to Focus (3-5 tags), Recommended Resources (2-3 bullets). "
        "Use short bullet points."
    )

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            headers={
                'Content-Type': 'application/json',
                'X-goog-api-key': GEMINI_API_KEY,
            },
            json={
                'contents': [
                    {
                        'role': 'user',
                        'parts': [
                            {'text': prompt}
                        ]
                    }
                ]
            },
            timeout=20
        )
        if resp.status_code != 200:
            # Pass through truncated error body for easier debugging (safe: no secrets)
            return jsonify({'error': f'Gemini API error {resp.status_code}: {resp.text[:300]}'}), 502

        data = resp.json()

        # Robust parsing against safety blocks / empty candidates
        text = ''
        candidates = data.get('candidates') or []
        if candidates:
            content = candidates[0].get('content') or {}
            parts = content.get('parts') or []
            # Join all text parts if available
            collected = []
            for p in parts:
                t = p.get('text') or ''
                if t:
                    collected.append(t)
            text = '\n'.join(collected).strip()
        if not text:
            # Fallback to stringified body to surface any useful info
            text = str(data)

        # Convert basic markdown (* bullets and headings) to HTML cards
        lines = [ln.strip() for ln in text.split('\n')]
        cards = []
        current = []
        current_title = 'Roadmap'

        def flush():
            if not current:
                return
            # Build HTML with bullet conversion
            html_parts = []
            in_ul = False
            for ln in current:
                if ln.startswith('* '):
                    if not in_ul:
                        html_parts.append('<ul class="mb-2">')
                        in_ul = True
                    html_parts.append('<li>' + ln[2:].strip() + '</li>')
                else:
                    if in_ul:
                        html_parts.append('</ul>')
                        in_ul = False
                    if ln:
                        html_parts.append('<p class="mb-2">' + ln.replace('**', '') + '</p>')
            if in_ul:
                html_parts.append('</ul>')
            cards.append(
                '<div class="stage-card card shadow-sm border-0 mb-3">'
                f'  <div class="card-header bg-dark text-white fw-semibold">{current_title}</div>'
                '  <div class="card-body">' + ''.join(html_parts) + '</div>'
                '</div>'
            )
            current.clear()

        # Heuristic: split by headings that don’t start with *
        for ln in lines:
            lower = ln.lower()
            if ln and not ln.startswith('* ') and (lower.startswith('foundational') or lower.startswith('intermediate') or lower.startswith('advanced')):
                flush()
                current_title = ln.replace('**', '')
            else:
                current.append(ln)
        flush()

        html = (
            '<div class="ai-roadmap">'
            '<div class="alert alert-info mb-3"><i class="fas fa-wand-magic me-2"></i><strong>Generated with Gemini</strong></div>'
            + ''.join(cards) +
            '</div>'
        )
        return jsonify({'html': html})
    except requests.HTTPError as e:
        return jsonify({'error': f'Gemini API error: {getattr(e.response, "text", str(e))[:300]}' }), 502
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {e}'}), 500


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db_path = os.path.join(os.path.dirname(__file__), 'interview_prep.db')
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

@app.route('/login/google')
def login_google():
    """Redirect user to Google OAuth"""
    if 'google' not in oauth._clients:
        flash('Google Sign-In not configured on server', 'error')
        return redirect(url_for('login'))
    redirect_uri = url_for('auth_google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def auth_google_callback():
    """Google OAuth callback handler"""
    if 'google' not in oauth._clients:
        flash('Google Sign-In not configured on server', 'error')
        return redirect(url_for('login'))
    # Handle error or missing code gracefully
    if 'error' in request.args:
        flash(request.args.get('error_description', request.args.get('error', 'Google sign-in cancelled')), 'error')
        return redirect(url_for('login'))
    if 'code' not in request.args:
        flash('Invalid OAuth response. Please try signing in again.', 'error')
        return redirect(url_for('login'))

    token = oauth.google.authorize_access_token()
    userinfo = token.get('userinfo') or oauth.google.parse_id_token(token)
    if not userinfo:
        flash('Failed to fetch profile from Google', 'error')
        return redirect(url_for('login'))

    email = userinfo.get('email')
    name = userinfo.get('name') or email.split('@')[0]

    # Ensure local user exists
    db_path = os.path.join(os.path.dirname(__file__), 'interview_prep.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    if not row:
        cursor.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                       (name, email, 'google-oauth'))
        conn.commit()
        user_id = cursor.lastrowid
        user_name = name
    else:
        user_id, user_name = row[0], row[1]
    conn.close()

    session['user_id'] = user_id
    session['user_name'] = user_name
    flash('Logged in with Google', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """User dashboard - requires authentication"""
    if 'user_id' not in session:
        flash('Please login to access dashboard', 'error')
        return redirect(url_for('login'))
    
    # Get user statistics
    db_path = os.path.join(os.path.dirname(__file__), 'interview_prep.db')
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
        from datetime import date, timedelta as _td
        today = date.today()
        current_date = today
        
        for practice_date in practice_dates:
            practice_date_obj = datetime.strptime(practice_date, '%Y-%m-%d').date()
            if current_date == practice_date_obj:
                current_streak += 1
                current_date -= _td(days=1)
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
    try:
        # Get the directory where this script (app.py) is located
        base_dir = os.path.dirname(os.path.abspath(__file__))
        q_path = os.path.join(base_dir, 'backend', 'data', 'questions.json')
        print('Loading questions from:', q_path)
        with open(q_path, 'r') as f:
            data = json.load(f)
            print('Loaded', len(data['questions']), 'questions')
            return data['questions']
    except Exception as e:
        print('Error loading questions:', e)
        return []

# @app.route("/practice")
# def practice_page():
#     if "user_id" not in session:
#         return redirect(url_for("login"))
#     return render_template("practice_page")

@app.route("/practice")
def practice_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("practice.html")

@app.route("/resume")
def resume():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("resume.html")

@app.route("/api/gemini/resume", methods=["POST"])
def gemini_resume():
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "Not authenticated"}), 401
    data = request.get_json(force=True, silent=True) or {}
    profile = data.get("profile") or {}  # {name,email,phone,location,linkedin,github,summary}
    skills  = data.get("skills") or []   # list of strings or {name,level}
    projects= data.get("projects") or [] # [{name,tech,desc,impact,links}]
    experience = data.get("experience") or [] # [{company,role,start,end,desc,impact}]
    education = data.get("education") or []   # [{degree,school,year,score}]
    target = (data.get("target") or "Software Engineer").strip()
    seniority = (data.get("seniority") or "Fresher").strip()

    if not GEMINI_API_KEY:
        return jsonify({"ok": False, "error": "GEMINI_API_KEY not configured"}), 500

    prompt = (
        "You are an ATS and recruiter-optimized resume writer. "
        f"Target role: {target}; Seniority: {seniority}. "
        "Given candidate data (JSON below), produce:\n"
        "1) improvements: three bullet suggestions to strengthen resume; "
        "2) highlights: 5-8 power bullets quantified with STAR verbs; "
        "3) html: full resume sections (Summary, Skills, Experience, Projects, Education) as clean HTML using <section> and <ul><li> only; "
        "no external CSS, minimal inline classes (h5, small, ul). Use US English. Avoid placeholders.\n\n"
        "Candidate JSON:\n"
        f"{json.dumps({'profile':profile,'skills':skills,'projects':projects,'experience':experience,'education':education}, ensure_ascii=False)}\n\n"
        "Return strict JSON with keys: improvements (array), highlights (array), html (string)."
    )

    payload = {
        "contents": [{"role":"user","parts":[{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "response_mime_type": "application/json"
        }
    }

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            headers={"Content-Type":"application/json","X-goog-api-key":GEMINI_API_KEY},
            json=payload, timeout=25
        )
        if resp.status_code != 200:
            return jsonify({"ok": False, "error": f"Gemini error {resp.status_code}: {resp.text[:300]}"}), 502
        data = resp.json()
        parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
        text = "\n".join([p.get("text","") for p in parts if p.get("text")]).strip()
        try:
            out = json.loads(text) if text else {}
        except Exception:
            out = {}
        out.setdefault("improvements", [])
        out.setdefault("highlights", [])
        out.setdefault("html", "<section><h5>Resume</h5><p>No content</p></section>")
        return jsonify({"ok": True, "result": out})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Unexpected: {e}"}), 500


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
    
    # Save attempt to database (no mock session in this path)
    db_path = os.path.join(os.path.dirname(__file__), 'interview_prep.db')
    conn = sqlite3.connect(db_path)
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
    
    db_path = os.path.join(os.path.dirname(__file__), 'interview_prep.db')
    conn = sqlite3.connect(db_path)
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
    db_path = os.path.join(os.path.dirname(__file__), 'interview_prep.db')
    conn = sqlite3.connect(db_path)
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
    db_path = os.path.join(os.path.dirname(__file__), 'interview_prep.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO attempts (user_id, question_id, correct, user_answer, mock_session_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (session['user_id'], question_id, correct, user_answer, session['mock_session_id']))
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
    db_path = os.path.join(os.path.dirname(__file__), 'interview_prep.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Prefer counting correct answers tied to this mock session; fallback to old time-window if none
    cursor.execute('''
        SELECT COUNT(*) FROM attempts 
        WHERE user_id = ? AND correct = 1 AND mock_session_id = ?
    ''', (session['user_id'], mock_session_id))
    correct_answers = cursor.fetchone()[0]

    if correct_answers == 0 and questions_answered == 0:
        # Fallback (legacy behavior): approximate by recent attempts in last 30 minutes
        cursor.execute('''
            SELECT COUNT(*) FROM attempts 
            WHERE user_id = ? AND correct = 1 
            AND timestamp >= datetime('now', '-30 minutes')
        ''', (session['user_id'],))
        correct_answers = cursor.fetchone()[0]
        # Attempt to infer questions_answered if none set
        cursor.execute('''
            SELECT COUNT(*) FROM attempts 
            WHERE user_id = ?
            AND timestamp >= datetime('now', '-30 minutes')
        ''', (session['user_id'],))
        questions_answered = session.get('mock_questions_answered', 0) or cursor.fetchone()[0]
    
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
    
    score_pct = round((correct_answers / questions_answered * 100) if questions_answered > 0 else 0, 1)
    return jsonify({
        'success': True,
        'total_questions': questions_answered,
        'correct_answers': correct_answers,
        'score': score_pct
    })

@app.route('/mock/results')
def mock_results():
    """Show mock interview results"""
    if 'user_id' not in session:
        flash('Please login to view results', 'error')
        return redirect(url_for('login'))
    
    # Get latest mock session
    db_path = os.path.join(os.path.dirname(__file__), 'interview_prep.db')
    conn = sqlite3.connect(db_path)
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
    
    # Calculate duration using SQLite timestamp format "YYYY-MM-DD HH:MM:SS"
    def parse_sqlite_ts(ts):
        if not ts:
            return None
        try:
            return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
        except Exception:
            # Fallback: try ISO 8601 if stored differently
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except Exception:
                return None

    start_dt = parse_sqlite_ts(start_time)
    end_dt = parse_sqlite_ts(end_time)

    if start_dt and end_dt:
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
    
    db_path = os.path.join(os.path.dirname(__file__), 'interview_prep.db')
    conn = sqlite3.connect(db_path)
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

@app.route('/ai-interview', methods=['GET'])
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


try:
    from services.gemini_client import ask_gemini
except ImportError:
    # Fallback if services module not found
    def ask_gemini(prompt):
        return "AI service not available"

@app.route("/api/gemini/qa", methods=["POST"])
def gemini_qa():
    data = request.get_json(force=True) or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"ok": False, "error": "Empty prompt"}), 400
    answer = ask_gemini(prompt)
    return jsonify({"ok": True, "answer": answer})

@app.route("/api/resume/ai-generate", methods=["POST"])
def resume_ai_generate():
    """Generate a starter resume using AI from minimal info. Returns JSON structure."""
    body = request.get_json(force=True, silent=True) or {}
    first_name = (body.get("firstName") or "").strip() or "John"
    last_name = (body.get("lastName") or "").strip() or "Doe"
    email = (body.get("email") or "").strip() or "john.doe@example.com"
    phone = (body.get("phone") or "").strip() or "+1-555-555-5555"
    target_role = (body.get("role") or "Software Engineer").strip()

    if GEMINI_API_KEY:
        instruction = (
            "You are an expert resume writer. Based on minimal candidate info, "
            "create a concise, ATS-friendly software resume. Return STRICT JSON with keys: "
            "firstName, lastName, email, phone, location, linkedin, summary, "
            "experience: [{jobTitle, company, startDate, endDate, description}], "
            "education: [{degree, school, gradYear, gpa}], skills: [..], "
            "projects: [{name, url, description}]. Dates in MM/YYYY or 'Present'. Keep content realistic."
        )
        seed = (
            f"Name: {first_name} {last_name}\nEmail: {email}\nPhone: {phone}\nTarget Role: {target_role}"
        )
        try:
            ai_json = _gemini_call([
                {"text": instruction},
                {"text": "\nCandidate:"},
                {"text": seed}
            ], expect_json=True, temperature=0.3)
            if ai_json:
                try:
                    data = json.loads(ai_json)
                    data.setdefault("firstName", first_name)
                    data.setdefault("lastName", last_name)
                    data.setdefault("email", email)
                    data.setdefault("phone", phone)
                    return jsonify({"ok": True, "resume": data})
                except Exception:
                    pass
        except Exception:
            pass

    # Fallback template when AI not available or parsing failed
    from datetime import datetime
    year = datetime.utcnow().year
    fallback = {
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "phone": phone,
        "location": "Your City, Country",
        "linkedin": "https://www.linkedin.com/in/your-profile",
        "summary": f"Aspiring {target_role} with strong CS fundamentals and hands-on project experience.",
        "experience": [
            {"jobTitle": "{role}".format(role=target_role), "company": "Demo Company",
             "startDate": "06/{y}".format(y=year-1), "endDate": "Present",
             "description": "Built features, fixed bugs, collaborated with team, and wrote tests."}
        ],
        "education": [
            {"degree": "B.Tech in Computer Science", "school": "ABC University", "gradYear": str(year), "gpa": "8.0/10"}
        ],
        "skills": ["Python", "Flask", "JavaScript", "React", "SQL"],
        "projects": [
            {"name": "Portfolio Website", "url": "https://example.com", "description": "Personal portfolio with responsive UI."}
        ]
    }
    return jsonify({"ok": True, "resume": fallback})

@app.route("/api/resume/test", methods=["GET"])
def test_resume():
    """Test route to verify server is working."""
    return jsonify({"ok": True, "message": "Resume API is working"})

@app.route("/api/resume/generate", methods=["POST"])
def generate_resume():
    """Generate ATS-friendly resume with AI recommendations."""
    print("Resume generation endpoint called")  # Debug log
    
    if not GEMINI_API_KEY:
        print("No Gemini API key configured")  # Debug log
        return jsonify({"ok": False, "error": "Gemini API key not configured"})
    
    body = request.get_json(force=True, silent=True) or {}
    print(f"Received data: {body}")  # Debug log
    
    # Extract resume data
    personal_info = {
        "name": f"{body.get('firstName', '')} {body.get('lastName', '')}".strip(),
        "email": body.get('email', ''),
        "phone": body.get('phone', ''),
        "location": body.get('location', ''),
        "linkedin": body.get('linkedin', ''),
        "summary": body.get('summary', '')
    }
    
    experience = body.get('experience', [])
    education = body.get('education', [])
    projects = body.get('projects', [])
    skills = body.get('skills', [])
    
    # Create resume analysis prompt
    analysis_prompt = f"""
    Analyze this resume for ATS (Applicant Tracking System) compatibility and provide recommendations:
    
    PERSONAL INFO:
    Name: {personal_info['name']}
    Email: {personal_info['email']}
    Phone: {personal_info['phone']}
    Location: {personal_info['location']}
    LinkedIn: {personal_info['linkedin']}
    Summary: {personal_info['summary']}
    
    EXPERIENCE:
    {chr(10).join([f"- {exp.get('jobTitle', '')} at {exp.get('company', '')} ({exp.get('startDate', '')} - {exp.get('endDate', '')}): {exp.get('description', '')}" for exp in experience])}
    
    EDUCATION:
    {chr(10).join([f"- {edu.get('degree', '')} from {edu.get('school', '')} ({edu.get('gradYear', '')})" for edu in education])}
    
    SKILLS:
    {', '.join(skills)}
    
    PROJECTS:
    {chr(10).join([f"- {proj.get('name', '')}: {proj.get('description', '')}" for proj in projects])}
    
    Please provide:
    1. ATS Score (0-100) based on keyword optimization, formatting, and completeness
    2. Specific recommendations for improvement
    3. Missing keywords that should be added
    4. Formatting suggestions for better ATS parsing
    
    Return as JSON with keys: ats_score, recommendations (array of objects with title and description), missing_keywords, formatting_tips.
    """
    
    try:
        analysis_result = _gemini_call([{"text": analysis_prompt}], expect_json=True, temperature=0.2)
        
        if not analysis_result:
            # Fallback analysis without API
            ats_score = min(85, 60 + len(experience) * 5 + len(skills) * 2)
            recommendations = [
                {"title": "Add More Keywords", "description": "Include industry-specific keywords from job descriptions"},
                {"title": "Quantify Achievements", "description": "Add numbers and metrics to your experience descriptions"},
                {"title": "Optimize Summary", "description": "Write a compelling 2-3 line professional summary"}
            ]
            missing_keywords = ["leadership", "project management", "problem solving"]
            formatting_tips = ["Use standard section headers", "Avoid graphics and tables", "Use bullet points"]
        else:
            try:
                analysis = json.loads(analysis_result)
                ats_score = analysis.get('ats_score', 75)
                recommendations = analysis.get('recommendations', [])
                missing_keywords = analysis.get('missing_keywords', [])
                formatting_tips = analysis.get('formatting_tips', [])
            except:
                # Fallback if JSON parsing fails
                ats_score = 75
                recommendations = [{"title": "AI Analysis", "description": "Resume analyzed successfully"}]
                missing_keywords = []
                formatting_tips = []
        
        return jsonify({
            "ok": True,
            "ats_score": ats_score,
            "recommendations": recommendations,
            "missing_keywords": missing_keywords,
            "formatting_tips": formatting_tips
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

# Single unified run block; no secret prints
if __name__ == '__main__':
    # For development only; disable debug in production
    app.run(debug=True, host='0.0.0.0', port=8081, use_reloader=False)

# For Vercel deployment
def handler(request):
    return app(request.environ, lambda status, headers: None)

# Web Service (Flask) Overview

## App Entrypoint
- File: `backend/app.py`
- Development run: `python3 backend/app.py`
- Production (Render): `gunicorn --chdir backend --bind 0.0.0.0: wsgi:app`

## Routes
- GET /, /features, /resources, /career_roadmap
- Auth: GET/POST /login, /register, GET /logout
- Dashboard: GET /dashboard
- Practice: GET /practice, /dsa
- Mock interview: /mock, /mock/question, POST /mock/submit, POST /mock/end, GET /mock/results
- API: GET /api/stats, POST /submit-answer

## Templates & Static
- Templates: `frontend/templates`
- Static: `frontend/static`

## Session & Security
- Session-based auth (Flask session)
- Passwords hashed via Werkzeug
- CSRF not enabled (consider Flask-WTF for forms)

## Error Handling
- 404 → `errors/404.html`
- 500 → `errors/500.html`

## Environment
- Dev: Flask debug server
- Prod: Gunicorn + Render

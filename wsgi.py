import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app import app

# This is the WSGI entry point for Vercel
if __name__ == "__main__":
    app.run()

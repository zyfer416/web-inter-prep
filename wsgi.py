import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from index import app

# This is the WSGI application that gunicorn will use
application = app

if __name__ == "__main__":
    app.run()
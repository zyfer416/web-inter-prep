# This file is created for Render compatibility
# It imports the Flask app from index.py

from index import app

# This is the WSGI application
application = app

if __name__ == "__main__":
    app.run()

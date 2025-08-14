#!/usr/bin/env python3
"""
WSGI entry point for Web-Inter-Prep
This file is used by Render to start the Flask application
"""

from app import app

if __name__ == "__main__":
    app.run()

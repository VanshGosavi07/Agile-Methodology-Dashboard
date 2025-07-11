"""
WSGI Entry Point for Flask Application
This file serves as the entry point for WSGI servers like Gunicorn
"""

from main import app

if __name__ == "__main__":
    app.run()

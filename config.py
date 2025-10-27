import os
from datetime import timedelta

class Config:
    """
    Simple configuration for local development with SQLite database.
    No deployment or production settings included.
    """
    SECRET_KEY = 'dev-8BYkEfBA6O6donzWlSihBXox7C0sKR6b-secure'
    SESSION_COOKIE_NAME = 'agile_dashboard_session'
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # Neon PostgreSQL Database - Cloud Hosted
    SQLALCHEMY_DATABASE_URI = 'postgresql://neondb_owner:npg_fQsLY0z9AKwB@ep-dark-bread-a16beev8-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # File Upload Settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

    # Email Configuration - Gmail
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'vanshgosavi777@gmail.com'
    MAIL_PASSWORD = 'pfry ijwv scdb pcio'
    MAIL_DEFAULT_SENDER = 'vanshgosavi777@gmail.com'

    # Debug Settings
    DEBUG = True
    TESTING = False


# Single configuration for development
config = {
    'default': Config
}
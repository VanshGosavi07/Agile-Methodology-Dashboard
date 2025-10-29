import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file (development only)
# In production (App Engine), env vars come from app.yaml
if not os.getenv('GAE_ENV'):
    load_dotenv()

class Config:
    """
    Configuration loaded from environment variables (.env file).
    All secrets and sensitive data stored in .env for security.
    """
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-key-for-dev')
    SESSION_COOKIE_NAME = 'agile_dashboard_session'
    
    # Security settings - adjust for production
    # On App Engine, use secure cookies if using HTTPS
    is_production = os.getenv('GAE_ENV', '').startswith('standard')
    SESSION_COOKIE_SECURE = is_production  # True on App Engine (HTTPS)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # Database Configuration - Loaded from .env
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # File Upload Settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

    # Email Configuration - Loaded from .env
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

    # Cloudinary Configuration - Loaded from .env
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')

    # Debug Settings - Automatically disable in production
    DEBUG = not is_production  # False on App Engine, True locally
    TESTING = False
    
    # Production optimizations
    if is_production:
        # Optimize for production
        SQLALCHEMY_ENGINE_OPTIONS['pool_size'] = 5
        SQLALCHEMY_ENGINE_OPTIONS['max_overflow'] = 10


# Single configuration for development
config = {
    'default': Config
}
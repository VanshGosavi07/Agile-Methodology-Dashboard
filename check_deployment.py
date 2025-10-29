"""
Pre-Deployment Checklist Script
This script checks if your project is ready for Google App Engine deployment
"""

import os
import sys
from pathlib import Path

def check_file_exists(filename):
    """Check if a file exists"""
    path = Path(filename)
    if path.exists():
        print(f"✅ {filename} - Found")
        return True
    else:
        print(f"❌ {filename} - Missing")
        return False

def check_env_file():
    """Check if .env file exists and has required variables"""
    if not Path('.env').exists():
        print("❌ .env file - Missing (copy .env.example and fill in values)")
        return False
    
    print("✅ .env file - Found")
    
    # Check for required environment variables
    required_vars = [
        'SECRET_KEY',
        'DATABASE_URL',
        'MAIL_USERNAME',
        'MAIL_PASSWORD',
        'CLOUDINARY_CLOUD_NAME',
        'CLOUDINARY_API_KEY',
        'CLOUDINARY_API_SECRET'
    ]
    
    from dotenv import load_dotenv
    load_dotenv()
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def check_requirements():
    """Check if requirements.txt has necessary packages"""
    if not Path('requirements.txt').exists():
        print("❌ requirements.txt - Missing")
        return False
    
    with open('requirements.txt', 'r') as f:
        content = f.read()
        required_packages = ['Flask', 'gunicorn', 'psycopg2-binary', 'Flask-SQLAlchemy']
        missing = [pkg for pkg in required_packages if pkg not in content]
        
        if missing:
            print(f"⚠️  requirements.txt missing packages: {', '.join(missing)}")
            return False
        else:
            print("✅ requirements.txt - All required packages present")
            return True

def check_gcloud_installed():
    """Check if gcloud CLI is installed"""
    result = os.system('gcloud --version >nul 2>&1')
    if result == 0:
        print("✅ Google Cloud SDK - Installed")
        return True
    else:
        print("❌ Google Cloud SDK - Not installed")
        print("   Download from: https://cloud.google.com/sdk/docs/install")
        return False

def main():
    print("="*60)
    print("🚀 Google App Engine Deployment Readiness Check")
    print("="*60)
    print()
    
    checks = []
    
    print("📁 Checking Configuration Files:")
    print("-" * 60)
    checks.append(check_file_exists('app.yaml'))
    checks.append(check_file_exists('.gcloudignore'))
    checks.append(check_file_exists('requirements.txt'))
    checks.append(check_file_exists('main.py'))
    checks.append(check_file_exists('config.py'))
    
    print()
    print("🔐 Checking Environment Variables:")
    print("-" * 60)
    checks.append(check_env_file())
    
    print()
    print("📦 Checking Dependencies:")
    print("-" * 60)
    checks.append(check_requirements())
    
    print()
    print("🛠️  Checking Tools:")
    print("-" * 60)
    checks.append(check_gcloud_installed())
    
    print()
    print("="*60)
    
    if all(checks):
        print("✅ All checks passed! Your project is ready to deploy! 🎉")
        print()
        print("Next steps:")
        print("1. Run: gcloud init")
        print("2. Run: gcloud app create --region=us-central")
        print("3. Run: gcloud app deploy")
        print()
        print("📖 See DEPLOYMENT_GUIDE.md for detailed instructions")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print()
        print("💡 Common fixes:")
        print("   - Copy .env.example to .env and fill in your values")
        print("   - Install Google Cloud SDK")
        print("   - Ensure all required files are present")
    
    print("="*60)

if __name__ == '__main__':
    main()

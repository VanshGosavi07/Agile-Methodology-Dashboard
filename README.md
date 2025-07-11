# Agile Project Management Dashboard

A comprehensive Flask-based web application for managing agile projects, sprints, user stories, and tasks.

## Features

- User authentication with OTP verification
- Project management with sprint planning
- User story and task tracking
- Visual analytics and reporting
- Email notifications
- PDF report generation
- Admin dashboard

## Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd "Completed Project"
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   copy .env.example .env
   # Edit .env file with your configuration
   ```

5. **Run the application**
   ```bash
   python main.py
   # or
   python wsgi.py
   ```

## Vercel Deployment

### Prerequisites
- Vercel account
- Git repository with your code

### Deployment Steps

1. **Prepare for deployment**
   - Ensure all files are committed to git
   - Verify `vercel.json` configuration
   - Set up environment variables

2. **Deploy to Vercel**
   ```bash
   # Install Vercel CLI
   npm i -g vercel
   
   # Login to Vercel
   vercel login
   
   # Deploy
   vercel --prod
   ```

3. **Configure Environment Variables in Vercel Dashboard**
   - Go to your project in Vercel dashboard
   - Navigate to Settings > Environment Variables
   - Add the following variables:
     - `SECRET_KEY`: Your Flask secret key
     - `DATABASE_URL`: Your production database URL (PostgreSQL recommended)
     - `SENDER_EMAIL`: Email for sending notifications
     - `SENDER_PASSWORD`: App password for email
     - `VERCEL_ENV`: production (automatically set by Vercel)

4. **Database Setup**
   - For production, use PostgreSQL or another cloud database
   - Update `DATABASE_URL` environment variable
   - Run migrations if needed

### Important Notes for Vercel Deployment

1. **Database**: SQLite doesn't work well with serverless environments. Use PostgreSQL, MySQL, or another cloud database for production.

2. **File Storage**: Vercel's filesystem is read-only. For file uploads and reports:
   - Use cloud storage (AWS S3, Cloudinary, etc.) for file uploads
   - Generate reports in memory or use cloud storage

3. **Scheduled Tasks**: Background threads don't work in serverless environments. Use:
   - Vercel Cron Jobs
   - External cron services
   - Manual trigger endpoints (already implemented: `/generate-report/<type>`)

4. **Environment Variables**: Never commit sensitive data. Use Vercel's environment variable system.

## Project Structure

```
├── main.py                 # Main Flask application
├── wsgi.py                # WSGI entry point
├── database.py            # Database configuration
├── models.py              # Database models
├── password_utils.py      # Password utilities
├── send_mail.py          # Email utilities
├── vercel.json           # Vercel configuration
├── requirements-production.txt  # Production dependencies
├── runtime.txt           # Python version specification
├── routers/              # Route blueprints
├── templates/            # HTML templates
├── static/              # Static files (CSS, JS, images)
└── instance/            # Local database (development only)
```

## API Endpoints

### Authentication
- `POST /auth/` - User login
- `POST /auth/add_user` - User registration
- `POST /auth/logout` - User logout
- `POST /auth/verify_otp` - OTP verification

### Projects
- `GET /projects/<role>/<userid>` - User dashboard
- `POST /submit` - Create new project
- `GET /editproject/<id>` - Edit project
- `GET /viewproject/<id>` - View project details

### Reports
- `GET /summary` - Project summary
- `GET /export-pdf` - Export PDF report
- `GET /generate-report/<type>` - Manual report generation

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key | Yes |
| `DATABASE_URL` | Database connection URL | Production |
| `SENDER_EMAIL` | Email for notifications | Yes |
| `SENDER_PASSWORD` | Email app password | Yes |
| `VERCEL_ENV` | Vercel environment | Auto-set |
| `FLASK_DEBUG` | Debug mode | No |

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify `DATABASE_URL` is correct
   - Ensure database is accessible from Vercel

2. **Email Issues**
   - Check `SENDER_EMAIL` and `SENDER_PASSWORD`
   - Ensure app passwords are enabled for Gmail

3. **Import Errors**
   - Verify all dependencies in `requirements-production.txt`
   - Check Python version compatibility

4. **Static Files Not Loading**
   - Ensure static files are in the correct directory
   - Check static file paths in templates

### Support

For issues and questions, please check:
1. Vercel documentation
2. Flask documentation
3. Project logs in Vercel dashboard

## License

This project is developed for educational purposes.

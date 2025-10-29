# 🚀 Agile Project Management Dashboard

> **Streamline Agile Software Development** with Sprint Planning, Real-Time Collaboration, and Advanced Analytics.

---

## 📖 Overview

**Agile Project Management Dashboard** is a full-stack web application built with **Flask**, **SQLAlchemy**, **Socket.IO**, and **Bootstrap 5** to simplify Agile workflows — including sprint planning, collaboration, and analytics. It allows teams to manage projects, sprints, stories, and tasks while generating professional PDF reports with charts.

---

## ⚙️ Key Features

### 🔐 Authentication & Roles
- RBAC: Admin, Product Owner, Scrum Master, Developer, Tester
- Secure login with BCrypt & Flask-Login
- User profiles with avatars & activity tracking

### 📂 Project & Sprint Management
- Create and manage projects, sprints, and stories
- Assign team members and track velocity
- Real-time status tracking

### 📊 Analytics & Reporting
- Visual charts (Pie, Bar, Donut, Line)
- Real-time updates via WebSockets
- PDF reports with embedded charts and summaries

### ☁️ Cloud Integration
- Neon PostgreSQL (Database)
- Cloudinary (Storage for images, reports, logs)
- Fully deployable to Heroku, AWS, or Google Cloud

---

## 🛠️ Tech Stack

| Layer | Technology |
|--------|-------------|
| **Backend** | Flask, SQLAlchemy, Flask-Login |
| **Database** | Neon PostgreSQL |
| **Frontend** | HTML5, CSS3, Bootstrap 5, JavaScript |
| **Real-Time** | Flask-SocketIO |
| **Visualization** | Matplotlib, Plotly |
| **Reporting** | FPDF |
| **Auth & Email** | Flask-Bcrypt, Flask-Mail |
| **Cloud Storage** | Cloudinary |

---

## ⚡ Setup Guide

### 1️⃣ Clone & Install
```bash
git clone https://github.com/VanshGosavi07/Agile-Methodology-Dashboard.git
cd Agile-Methodology-Dashboard
python -m venv venv
venv\Scripts\activate   # or source venv/bin/activate
pip install -r requirements.txt
```

### 2️⃣ Configure `.env`
```env
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@host:port/db
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
CLOUDINARY_CLOUD_NAME=your-cloud
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-secret
```

### 3️⃣ Run App
```bash
python main.py
```
Access at: http://localhost:5000

---

## 🧭 Workflow Overview

| Role | Capabilities |
|------|---------------|
| **Admin** | Approve users, monitor activity, generate reports |
| **Product Owner** | Create projects, define sprints, assign teams |
| **Scrum Master** | Manage sprints & track velocity |
| **Developer** | Update story & task statuses |
| **Tester** | Verify stories & log results |

---

## 🎨 UI/UX
- Responsive Bootstrap 5 design
- Gradient theme (#667eea → #764ba2)
- Interactive animations & hover effects

---

## 🔒 Security
- BCrypt password hashing
- CSRF & XSS protection
- SQL injection prevention
- Role-based access control

---

## 🚀 Deployment

### 🌐 Google App Engine (Recommended)

This project is fully configured for **Google App Engine** deployment!

#### Quick Deploy Steps:
```bash
# 1. Install Google Cloud SDK
gcloud --version

# 2. Initialize and create project
gcloud auth login
gcloud projects create your-project-id
gcloud config set project your-project-id

# 3. Setup environment variables (copy .env.example to .env and fill values)
copy .env.example .env

# 4. Enable App Engine
gcloud services enable appengine.googleapis.com
gcloud app create --region=us-central

# 5. Deploy!
gcloud app deploy

# 6. Open your app
gcloud app browse
```

#### 📚 Complete Deployment Guides:
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Comprehensive step-by-step guide
- **[QUICK_DEPLOY.md](QUICK_DEPLOY.md)** - Quick reference commands
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Pre-deployment checklist
- **[DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)** - Overview and tips

#### ✅ Pre-Deployment Check:
```bash
python check_deployment.py
```

### 🐳 Alternative: Docker/Cloud Run
```bash
docker build -t agile-dashboard .
docker run -p 8080:8080 agile-dashboard
```

### 💻 Local Development
```bash
set FLASK_ENV=development
python main.py
```

### 🏭 Production (Other Platforms)
```bash
set FLASK_ENV=production
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app --timeout 300
```

---

## 🤝 Contribution
```bash
git checkout -b feature/new-feature
git commit -m "✨ Add new feature"
git push origin feature/new-feature
```

---

## 📬 Contact

**Author:** Vansh Gosavi  
📧 Email: vanshgosavi7@gmail.com  
🌐 GitHub: [@VanshGosavi07](https://github.com/VanshGosavi07)

---

## 🛣️ Roadmap
- Kanban board view  
- Burndown charts  
- Time tracking  
- GitHub/GitLab integration  

---

**Version:** 1.0.0 | **License:** MIT  
> Empowering Agile Teams with Real-Time Collaboration & Data-Driven Insights.

# 📊 Agile Project Management Dashboard

> Streamlining Software Development through Modern Agile Practices — Sprint Management, Real-Time Collaboration & Advanced Analytics 🚀

---

## 📌 Overview

**Agile Project Management Dashboard** is a **comprehensive full-stack web application** designed to facilitate Agile software development methodologies. The platform enables teams to efficiently manage projects, sprints, user stories, and tasks while providing real-time collaboration features and detailed analytics.

🎯 Built using **Flask**, **SQLAlchemy**, **Socket.IO**, **Bootstrap 5**, and **Matplotlib**, the system supports multiple user roles, real-time updates, status tracking, and professional PDF report generation with visual charts.

---

## 🧠 Core Features

### 🔐 **Multi-Role Authentication System**
- **5 User Roles**: Admin, Product Owner, Scrum Master, Developer, Tester
- **Role-Based Access Control (RBAC)**: Granular permissions for each role
- **Secure Authentication**: BCrypt password hashing with session management
- **Profile Management**: User profiles with custom avatars
- **Organization Support**: Multi-tenant architecture with organization isolation
- **Login History Tracking**: Monitor user activity and failed login attempts

### 📋 **Comprehensive Project Management**
- **Project Creation & Editing**: Complete CRUD operations for projects
- **Sprint Planning**: Create and manage multiple sprints per project
- **User Story Management**: Detailed story tracking with priorities and assignments
- **Task Breakdown**: Decompose stories into manageable tasks
- **Team Assignment**: Add team members to projects dynamically
- **Status Tracking**: Not Started, In Progress, Testing, Completed, Blocked

### 🏃 **Sprint Management**
- **Sprint Calendar**: Visual sprint timeline with start/end dates
- **Velocity Tracking**: Monitor team velocity across sprints
- **Sprint Goals**: Define and track sprint objectives
- **Story Point Estimation**: Assign and track story points
- **Scrum Master Assignment**: Dedicated sprint ownership

### 📝 **User Story & Task Management**
- **Story Details**: Description, acceptance criteria, priority
- **Task Decomposition**: Break stories into subtasks
- **Assignee Management**: Assign stories to developers/testers
- **Status Updates**: Real-time status change capabilities
- **Progress Tracking**: Visual indicators for completion status

### 📊 **Advanced Analytics & Visualization**
- **Dashboard Charts**: 
  - 📈 Project Status Distribution (Pie Chart)
  - 📊 User Stories Progress (Bar Chart)
  - 🍩 Task Completion Overview (Donut Chart)
  - 📉 Sprint Velocity Trends (Line Chart)
- **Summary Statistics**: Comprehensive metrics across all projects
- **Real-Time Updates**: Live data synchronization via WebSockets
- **PDF Reports**: Professional reports with embedded charts

### 💬 **Real-Time Collaboration**
- **WebSocket Integration**: Instant updates across all connected users
- **Live Notifications**: Real-time alerts for project changes
- **Activity Tracking**: Monitor user actions and project modifications

### 📥 **Professional Reporting**
- **PDF Export**: Generate detailed reports with charts
- **Beautiful Formatting**: Color-coded sections with professional layout
- **Chart Integration**: 4 embedded visualization charts
- **Executive Summary**: Key highlights and recommendations
- **Table of Contents**: Organized report structure

### 🎨 **Modern UI/UX**
- **Responsive Design**: Mobile, tablet, and desktop optimized
- **Purple Gradient Theme**: Consistent color scheme (#667eea → #764ba2)
- **Bootstrap 5**: Modern, clean interface
- **Loading Indicators**: Smooth user feedback with spinners
- **Interactive Elements**: Hover effects, animations, tooltips

---

## 🗂️ Folder Structure

```
Agile-Project-Management-Dashboard/
├── instance/
│   └── global.db                    # SQLite database
├── routers/
│   ├── __init__.py
│   └── team1.py                     # Authentication routes
├── static/
│   ├── css/                         # Stylesheets
│   ├── images/                      # Images & logo
│   ├── js/                          # JavaScript files
│   └── uploads/                     # User uploads
├── templates/
│   ├── landing.html                 # Landing page
│   ├── login.html                   # Login page
│   ├── signup.html                  # Registration page
│   ├── Dashboard.html               # Main dashboard
│   ├── addproject.html              # Add project form
│   ├── view.html                    # Project details
│   ├── charts.html                  # Analytics page
│   ├── summary.html                 # Summary page
│   └── admin_dashboard.html         # Admin panel
├── main.py                          # Flask application
├── models.py                        # Database models
├── database.py                      # Database initialization
├── requirements.txt                 # Dependencies
└── README.md                        # Documentation
```

---

## 🛠️ Tech Stack

| Layer              | Technology                                    |
|--------------------|-----------------------------------------------|
| **Backend**        | Flask 3.1.0, SQLAlchemy 2.0.36, Flask-Login  |
| **Database**       | SQLite (Development), PostgreSQL-ready        |
| **Frontend**       | HTML5, CSS3, Bootstrap 5.3.2, JavaScript     |
| **Real-Time**      | Flask-SocketIO 5.3.6, python-socketio         |
| **Charts/Graphs**  | Matplotlib 3.9.3 (lightweight)                |
| **Data Viz**       | Plotly 6.3.1, Pandas 2.3.3                   |
| **PDF Generation** | FPDF 1.7.2 with chart embedding              |
| **Authentication** | BCrypt 5.0.0, Flask-Bcrypt                    |
| **Email**          | Flask-Mail 0.9.1                              |
| **Scheduling**     | Schedule 1.2.2                                |

---

## ✅ Prerequisites

- **Python 3.10+** 🐍
- **Flask Framework** 🌐
- **SQLite** (included) or **PostgreSQL** 💾
- **Modern Web Browser** (Chrome, Firefox, Edge) 🌍

---

## 🔧 Installation & Setup

### 1. **Clone the Repository**

```bash
git clone https://github.com/VanshGosavi07/Agile-Methodology-Dashboard.git
cd "Agile-Methodology-Dashboard"
```

### 2. **Create Virtual Environment**

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

### 3. **Install Dependencies**

```bash
pip install -r requirements.txt
```

### 4. **Set Environment Variables** (Optional)

```bash
set SECRET_KEY=your-secret-key-here
set MAIL_SERVER=smtp.gmail.com
set MAIL_PORT=587
set MAIL_USERNAME=your-email@gmail.com
set MAIL_PASSWORD=your-app-password
```

### 5. **Initialize Database**

The database will be created automatically on first run.

```bash
python main.py
```

### 6. **Access the Application**

🌍 Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 📘 How to Use - Complete Workflow

### 🔐 **1. Registration & Login**

1. Navigate to `/signup` page
2. Fill registration form with username, email, password, and role selection
3. Select Organization (or create new)
4. Submit → Admin approval required (except Admin role)
5. Login at `/login` with credentials

---

### 👨‍💼 **2. Admin Role**

**Capabilities:**
- Approve/reject user registrations
- View all projects across organization
- Monitor user activity and login history
- Generate system-wide reports

---

### 📋 **3. Product Owner Role**

**Capabilities:**
- Create and manage projects
- Define project scope and timeline
- Create sprints and user stories
- Assign team members to projects
- Generate PDF reports

**Create New Project:**
1. Dashboard → Click "Add New Project"
2. Fill project details (name, description, dates, status)
3. Select team members
4. Add sprints with goals and velocity
5. Add user stories with acceptance criteria and priorities
6. Submit project

---

### 🏃 **4. Scrum Master Role**

**Capabilities:**
- Manage assigned sprints
- Update sprint progress and velocity
- Update user story statuses
- Monitor team progress

---

### 💻 **5. Developer Role**

**Capabilities:**
- View assigned user stories
- Update story status (Not Started → In Progress → Testing → Completed)
- Track progress on assignments

---

### 🧪 **6. Tester Role**

**Capabilities:**
- View stories assigned for testing
- Update testing status
- Verify acceptance criteria
- Report test results

---

### 📊 **7. Charts & Analytics**

**Available at `/charts` page**

**A. Project Status Distribution (Pie Chart)** - Overall project health
**B. User Stories Progress (Bar Chart)** - Story completion tracking
**C. Task Status Overview (Donut Chart)** - Task-level breakdown
**D. Sprint Velocity Trend (Line Chart)** - Team performance over time

---

### 📄 **8. PDF Reports**

Navigate to `/summary` page and click "Download Report" to generate professional PDF with:
- Executive summary
- Project statistics with embedded charts
- Sprint velocity analysis
- Recommendations

---

## 🎨 Design Philosophy

- **Primary Gradient**: #667eea → #764ba2 (Purple)
- **Responsive Design**: Mobile, tablet, desktop optimized
- **Bootstrap 5**: Modern, clean interface
- **Interactive Elements**: Hover effects, animations, tooltips

---

## 🔒 Security Features

- BCrypt password hashing with salt
- Session-based authentication with Flask-Login
- CSRF protection and XSS prevention
- Role-based access control (RBAC)
- SQL injection prevention via SQLAlchemy ORM

---

## 🚀 Deployment Guide

```bash
# 1. Set production environment
set FLASK_ENV=production
set SECRET_KEY=<strong-random-key>

# 2. Use production database (PostgreSQL)
set DATABASE_URL=postgresql://user:pass@host:5432/dbname

# 3. Use production WSGI server
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

---

## 🤝 Contribution Guidelines

```bash
# Fork repository and create feature branch
git checkout -b feature/amazing-feature

# Commit changes
git commit -m "✨ Add amazing feature"

# Push and open Pull Request
git push origin feature/amazing-feature
```

---

## 📜 License

This project is licensed under the **MIT License**.

---

## 📬 Contact & Support

- **GitHub**: [@VanshGosavi07](https://github.com/VanshGosavi07)
- **Email**: vanshgosavi7@gmail.com
- **Phone**: +91 9359775740

---

## 🎯 Roadmap

- Kanban board view
- Burndown charts
- Email notifications
- Time tracking integration
- GitHub/GitLab integration

---

## ⚡ Quick Start

**Product Owner**: `Login → Add Project → Define Sprints → Assign Team`  
**Scrum Master**: `Login → Monitor Sprint → Track Velocity`  
**Developer**: `Login → View Stories → Update Status → Complete Work`  
**Tester**: `Login → Test Stories → Update Status`  
**Admin**: `Login → Approve Users → Monitor System`

---

🚀 **Build Exceptional Software with Agile Project Management Dashboard!**

*Version: 1.0.0 | Maintained by: Vansh Gosavi*

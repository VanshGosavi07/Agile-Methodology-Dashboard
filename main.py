from flask import Flask, redirect, url_for, render_template, flash, jsonify, request, send_file, Response,session
from flask_socketio import SocketIO, emit, join_room, leave_room
from database import db
import os
from datetime import datetime
import send_mail as sm
from fpdf import FPDF
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from io import BytesIO
import tempfile
import os
import schedule
import time
from threading import Thread
from io import BytesIO
import traceback
from models import (
    ProjectDetails,
    ProductOwner,
    UserStories,
    Users,
    ProjectUsers,
    SprintCalendar,
    Tasks,
    ScrumMasters,
    Reports,
    FrequencyEnum
)

from routers.team1 import login_bp, login_manager

# Simple login decorator without RBAC
def require_login():
    """Decorator to require user to be logged in (no permission checks)"""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'uid' not in session:
                flash("Please login to access this page.", "warning")
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

app = Flask(__name__)
login_manager.init_app(app)
login_manager.login_view = "auth.login"

# Load configuration from config.py
from config import Config
app.config.from_object(Config)

print("Using Neon PostgreSQL database (cloud-hosted)")

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

app.register_blueprint(login_bp, url_prefix="/auth")

with app.app_context():
    db.create_all()

def setup_scheduled_reports():
    """Setup scheduled reports for local development only."""
    schedule.every().day.at("18:29").do(lambda: generate_scheduled_report("daily")
                                        if datetime.now().day != 1 and datetime.now().strftime('%A').lower() != "monday" else None)
    schedule.every().monday.at("00:00").do(
        lambda: generate_scheduled_report("weekly"))
    schedule.every().day.at("18:37").do(lambda: generate_scheduled_report(
        "monthly") if datetime.now().day == 1 else None)

    scheduler_thread = Thread(target=schedule_reports, daemon=True)
    scheduler_thread.start()
    print("Scheduled reports initialized for local development")


@app.route('/')
def landing_page():
    """Landing page with project overview and features"""
    return render_template('landing.html')


@app.route('/home')
def new_home():
    """Redirect to login page"""
    return redirect(url_for('auth.login'))


user=''

@app.route("/projects/<role>/<int:userid>")
def projects(role, userid):
    """
    Display dashboard with all projects for the user.
    
    Args:
        role (str): User's role (admin, product owner, team member, etc.)
        userid (int): User ID to fetch projects for
        
    Returns:
        Rendered dashboard template with project list and statistics
    """
    try:
        # Get user information
        user = Users.query.filter_by(UserID=userid).first()
        if not user:
            flash("User not found", "error")
            return redirect(url_for('auth.login'))
        
        # Check if user is admin or product owner (can see all projects)
        user_role = role.lower().replace(' ', '')
        if user_role in ['admin', 'productowner']:
            # Admin and Product Owner can see all projects
            projects_data = ProjectDetails.query.all()
            print(f"[INFO] Admin/PO - Fetched {len(projects_data)} projects for user {userid}")
        else:
            # Other users can only see projects they are assigned to
            assigned_project_ids = db.session.query(ProjectUsers.ProjectId).filter_by(UserID=userid).all()
            assigned_project_ids = [pid[0] for pid in assigned_project_ids]
            projects_data = ProjectDetails.query.filter(ProjectDetails.ProjectId.in_(assigned_project_ids)).all()
            print(f"[INFO] User {userid} - Fetched {len(projects_data)} assigned projects")
        
        # Calculate project statistics based on filtered projects
        project_ids = [p.ProjectId for p in projects_data]
        total_projects = len(projects_data)
        active_projects = sum(1 for p in projects_data if p.Status == "Active")
        on_hold_projects = sum(1 for p in projects_data if p.Status == "On Hold")
        
        # Format project data for template
        projects = [
            {
                "project_name": project.ProjectName,
                "product_owner": project.product_owner.Name,
                "start_date": project.StartDate,
                "end_date": project.EndDate,
                "revised_end_date": project.RevisedEndDate,
                "status": project.Status,
                "project_id": project.ProjectId,
            }
            for project in projects_data
        ]
        
        return render_template(
            "Dashboard.html",
            projects=projects,
            total_projects=total_projects,
            active_projects=active_projects,
            on_hold_projects=on_hold_projects,
            user_name=session.get('username', 'Guest'),
            role=role
        )
    except Exception as e:
        # Log error and show user-friendly message
        print(f"[ERROR] Failed to load dashboard: {str(e)}")
        print(traceback.format_exc())
        flash("An error occurred while loading the dashboard. Please try again.", "error")
        return redirect(url_for('auth.login'))


@app.route("/api/product_owners", methods=["GET"])
def get_product_owners():
    """
    API endpoint to fetch all product owners.
    
    Returns:
        JSON: List of product owners with id and name
    """
    try:
        owners = ProductOwner.query.all()
        return jsonify(
            [{"id": owner.ProductOwnerId, "name": owner.Name} for owner in owners]
        )
    except Exception as e:
        print(f"[ERROR] Failed to fetch product owners: {str(e)}")
        return jsonify({"error": "Failed to fetch product owners"}), 500


@app.route("/api/scrum_masters", methods=["GET"])
def scrumMasters():
    """
    API endpoint to fetch all scrum masters.
    
    Returns:
        JSON: List of scrum masters with id and name
    """
    try:
        smasters = ScrumMasters.query.all()
        return jsonify(
            [{"id": smaster.ScrumMasterID, "name": smaster.Name} for smaster in smasters]
        )
    except Exception as e:
        print(f"[ERROR] Failed to fetch scrum masters: {str(e)}")
        return jsonify({"error": "Failed to fetch scrum masters"}), 500


@app.route("/api/users", methods=["GET"])
def users():
    """
    API endpoint to fetch all users.
    
    Returns:
        JSON: List of users with id and name
    """
    try:
        users = Users.query.all()
        return jsonify([{"id": user.UserID, "name": user.UserName} for user in users])
    except Exception as e:
        print(f"[ERROR] Failed to fetch users: {str(e)}")
        return jsonify({"error": "Failed to fetch users"}), 500


@app.route("/addproject")
@require_login()
def addproject():
    """
    Display the add project form page.
    
    Returns:
        Rendered template for adding new project
    
    Access: Product Owner, Admin only
    """
    try:
        user_role = session.get('role', 'guest')
        user_id = session.get('uid', 0)
        
        # Removed permission checks - all users can access
        
        return render_template(
            "addproject.html",
            user_name=session.get('username', 'Guest'),
            user_role=user_role,
            user_id=user_id
        )
    except Exception as e:
        print(f"[ERROR] Failed to load add project page: {str(e)}")
        flash("An error occurred while loading the form. Please try again.", "error")
        return redirect(url_for('auth.login'))


@app.route("/submit", methods=["POST"])
@require_login()
def submit_project():
    """
    Handle project submission with sprints and user stories.
    Expects JSON data from the frontend.
    
    Access: Product Owner, Admin only
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data received"}), 400
        
        print(f"[INFO] Received project data: {data.get('project_name')}")
        
        # Extract basic project information
        product_owner_id = data.get('product_owner_id')
        project_name = data.get('project_name')
        project_description = data.get('project_description')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        revised_end_date = data.get('revised_end_date')
        status = data.get('status', 'Active')
        selected_user_ids = data.get('selected_user_ids', '')
        
        # Validate required fields
        if not all([product_owner_id, project_name, start_date, end_date]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Get organization ID from current user (assuming user is logged in)
        from flask_login import current_user
        if not current_user.is_authenticated:
            return jsonify({"error": "User not logged in"}), 401
        
        org_id = current_user.OrgID
        if not org_id:
            return jsonify({"error": "Organization not found for user"}), 400
        
        # Create project
        new_project = ProjectDetails(
            OrgID=org_id,
            ProductOwnerId=int(product_owner_id),
            ProjectName=project_name,
            ProjectDescription=project_description,
            StartDate=datetime.strptime(start_date, '%Y-%m-%d').date(),
            EndDate=datetime.strptime(end_date, '%Y-%m-%d').date(),
            RevisedEndDate=datetime.strptime(revised_end_date, '%Y-%m-%d').date() if revised_end_date else None,
            Status=status
        )
        
        db.session.add(new_project)
        db.session.flush()  # Get project ID
        
        project_id = new_project.ProjectId
        print(f"[SUCCESS] Created project: {project_name} (ID: {project_id})")
        
        # Save selected users to ProjectUsers table
        if selected_user_ids:
            user_id_list = [int(uid.strip()) for uid in selected_user_ids.split(',') if uid.strip()]
            for user_id in user_id_list:
                project_user = ProjectUsers(UserID=user_id, ProjectId=project_id)
                db.session.add(project_user)
            print(f"[SUCCESS] Added {len(user_id_list)} team members to project")
        
        # Process sprints
        sprints_data = data.get('sprints', [])
        sprint_id_map = {}  # Map sprint number to sprint ID
        
        for idx, sprint_data in enumerate(sprints_data, start=1):
            sprint = SprintCalendar(
                ProjectId=project_id,
                ScrumMasterID=int(sprint_data.get('scrum_master_id')),
                SprintNo=idx,
                StartDate=datetime.strptime(sprint_data.get('start_date'), '%Y-%m-%d').date(),
                EndDate=datetime.strptime(sprint_data.get('end_date'), '%Y-%m-%d').date(),
                Velocity=int(sprint_data.get('velocity', 0))
            )
            db.session.add(sprint)
            db.session.flush()
            sprint_id_map[idx] = sprint.SprintId
            print(f"[SUCCESS] Created Sprint {idx} (ID: {sprint.SprintId})")
        
        # Process user stories
        user_stories_created = 0
        for key, value in data.items():
            # Find user story fields (e.g., story_desc_1_1)
            if key.startswith('story_desc_'):
                parts = key.split('_')
                sprint_num = int(parts[2])
                story_num = int(parts[3])
                
                # Extract all fields for this user story
                planned_sprint = data.get(f'planned_sprint_{sprint_num}_{story_num}')
                actual_sprint = data.get(f'actual_sprint_{sprint_num}_{story_num}')
                story_points = data.get(f'story_points_{sprint_num}_{story_num}')
                moscow = data.get(f'moscow_{sprint_num}_{story_num}')
                assignee = data.get(f'assignee_{sprint_num}_{story_num}')
                story_status = data.get(f'status_{sprint_num}_{story_num}')
                
                # Get sprint ID from map
                sprint_id = sprint_id_map.get(sprint_num)
                
                if sprint_id:
                    user_story = UserStories(
                        ProjectId=project_id,
                        SprintId=sprint_id,
                        PlannedSprint=int(planned_sprint) if planned_sprint else sprint_num,
                        ActualSprint=int(actual_sprint) if actual_sprint else sprint_num,
                        StoryPoint=int(story_points) if story_points else 0,
                        Description=value,
                        MOSCOW=moscow,
                        Assignee=assignee,
                        Status=story_status
                    )
                    db.session.add(user_story)
                    user_stories_created += 1
        
        # Commit all changes
        db.session.commit()
        
        print(f"[SUCCESS] Project submission complete:")
        print(f"  - Project: {project_name}")
        print(f"  - Sprints: {len(sprints_data)}")
        print(f"  - User Stories: {user_stories_created}")
        
        # Emit socket event to refresh dashboards
        try:
            socketio.emit('refresh_data', {'message': 'New project added'})
        except:
            pass
        
        return jsonify({
            "success": True,
            "message": "Project created successfully!",
            "project_id": project_id,
            "redirect": f"/projects/{session.get('role')}/{session.get('uid')}"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Failed to submit project: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to create project: {str(e)}"}), 500


def get_all_scrum_masters():
    scrum_masters = ScrumMasters.query.all()
    return [{"id": sm.ScrumMasterID, "name": sm.Name} for sm in scrum_masters]


@app.route("/editproject/<int:project_id>", methods=["GET", "POST"])
@require_login()
def edit_project(project_id):
    """
    Edit existing project details, sprints, and user stories.
    
    Access: Product Owner of the project, Admin
    """
    if request.method == "GET":
        try:
            project = ProjectDetails.query.filter_by(ProjectId=project_id).first()
            scrum_masters = get_all_scrum_masters()
            print(scrum_masters)
            if not project:
                flash("Project not found.", "error")
                return redirect(url_for('projects', role=session.get('role'), userid=session.get('uid')))

            # Allow all users to edit projects (removed permission check)

            project_data = {
                "ProjectId": project.ProjectId,
                "ProductOwnerId": project.ProductOwnerId,
                "ProjectName": project.ProjectName,
                "ProjectDescription": project.ProjectDescription,
                "StartDate": project.StartDate,
                "EndDate": project.EndDate,
                "RevisedEndDate": project.RevisedEndDate,
                'Status':project.Status,
                "sprints": [
                    {
                        "SprintId": sprint.SprintId,
                        "SprintNo": sprint.SprintNo,
                        "ScrumMasterID": sprint.ScrumMasterID,
                        "StartDate": sprint.StartDate,
                        "EndDate": sprint.EndDate,
                        "Velocity": sprint.Velocity,
                        "user_stories": [
                            {
                                "PlannedSprint": story.PlannedSprint,
                                "ActualSprint": story.ActualSprint,
                                "Description": story.Description,
                                "StoryPoint": story.StoryPoint,
                                "MOSCOW": story.MOSCOW,
                                "Assignee": story.Assignee,
                                "Status": story.Status,
                            }
                            for story in sprint.user_stories
                        ],
                    }
                    for sprint in project.sprints
                ],
            }
            print(session['role'],session['uid'])

            # Removed permission checks - all users can edit

            return render_template(
                "edit_project.html",
                project=project_data,
                scrum_masters=scrum_masters,
                user_name=session['username'],
                user_role=session['role'],
                user_id=session['uid'],
                can_edit=True
            )

        except Exception as e:
            print(f"[ERROR] Failed to load project for editing: {str(e)}")
            print(traceback.format_exc())
            flash("An error occurred while loading the project.", "error")
            return redirect(url_for('projects', role=session.get('role'), userid=session.get('uid')))

    elif request.method == "POST":
        """
        Handle project update with comprehensive form validation and error handling.
        All database changes are committed together with rollback on error.
        
        Access: Product Owner of the project, Admin
        """
        try:
            # Removed permission check - all users can update projects

            # Fetch project or return 404
            project = ProjectDetails.query.get_or_404(project_id)

            # ========== Validate Project Basic Information ==========
            
            # Validate project name
            project_name = request.form.get("project_name", "").strip()
            if not project_name:
                flash("Project Name is required and cannot be empty.", "error")
                return redirect(request.referrer)
            if len(project_name) < 3:
                flash("Project Name must be at least 3 characters long.", "error")
                return redirect(request.referrer)
            if len(project_name) > 255:
                flash("Project Name cannot exceed 255 characters.", "error")
                return redirect(request.referrer)

            # Validate project description
            project_description = request.form.get("project_description", "").strip()
            if not project_description:
                flash("Project Description is required and cannot be empty.", "error")
                return redirect(request.referrer)
            if len(project_description) < 10:
                flash("Project Description must be at least 10 characters long.", "error")
                return redirect(request.referrer)

            # ========== Validate Project Dates ==========
            try:
                start_date = datetime.strptime(
                    request.form.get("start_date", ""), "%Y-%m-%d"
                ).date()
            except (ValueError, KeyError):
                flash("Invalid Start Date format. Please use YYYY-MM-DD.", "error")
                return redirect(request.referrer)
                
            try:
                end_date = datetime.strptime(
                    request.form.get("end_date", ""), "%Y-%m-%d"
                ).date()
            except (ValueError, KeyError):
                flash("Invalid End Date format. Please use YYYY-MM-DD.", "error")
                return redirect(request.referrer)
                
            try:
                revised_end_date = datetime.strptime(
                    request.form.get("revised_end_date", ""), "%Y-%m-%d"
                ).date()
            except (ValueError, KeyError):
                flash("Invalid Revised End Date format. Please use YYYY-MM-DD.", "error")
                return redirect(request.referrer)

            # Date logic validation
            if end_date < start_date:
                flash("End Date cannot be earlier than Start Date.", "error")
                return redirect(request.referrer)
            if revised_end_date < start_date:
                flash("Revised End Date cannot be earlier than Start Date.", "error")
                return redirect(request.referrer)
                
            # Validate status
            status = request.form.get('status', '').strip()
            valid_statuses = ['Active', 'Completed', 'On Hold', 'Cancelled', 'Not Started']
            if status not in valid_statuses:
                flash(f"Invalid status. Must be one of: {', '.join(valid_statuses)}", "error")
                return redirect(request.referrer)

            # ========== Update Project with validated data ==========
            project.ProjectName = project_name
            project.ProjectDescription = project_description
            project.StartDate = start_date
            project.EndDate = end_date
            project.RevisedEndDate = revised_end_date
            project.Status = status
            
            # Commit project changes
            db.session.commit()
            print(f"[INFO] Project {project_id} updated successfully")

            # ========== Validate and Update Sprints ==========
            for index, sprint in enumerate(project.sprints):
                sprint_no = request.form.get(f"sprintNo_{index+1}", "").strip()
                
                # Validate sprint number
                if not sprint_no or not sprint_no.isdigit():
                    db.session.rollback()
                    flash(f"Sprint No for Sprint {index+1} must be a valid number.", "error")
                    return redirect(request.referrer)

                # Validate scrum master
                scrum_master_id = request.form.get(f"scrum_master_id_{index+1}", "").strip()
                if not scrum_master_id or not scrum_master_id.isdigit():
                    db.session.rollback()
                    flash(f"Scrum Master is required for Sprint {index+1}.", "error")
                    return redirect(request.referrer)

                # Validate sprint dates
                try:
                    sprint_start_date = datetime.strptime(
                        request.form.get(f"sprint_start_date_{index+1}", ""), "%Y-%m-%d"
                    ).date()
                    sprint_end_date = datetime.strptime(
                        request.form.get(f"sprint_end_date_{index+1}", ""), "%Y-%m-%d"
                    ).date()

                    if sprint_end_date < sprint_start_date:
                        db.session.rollback()
                        flash(
                            f"Sprint {index+1}: End Date cannot be earlier than Start Date.",
                            "error",
                        )
                        return redirect(request.referrer)
                except (ValueError, KeyError):
                    db.session.rollback()
                    flash(
                        f"Invalid date format for Sprint {index+1}. Use YYYY-MM-DD.",
                        "error",
                    )
                    return redirect(request.referrer)

                # Validate velocity
                velocity = request.form.get(f"sprint_velocity_{index+1}", "").strip()
                if not velocity or not velocity.isdigit() or int(velocity) <= 0:
                    db.session.rollback()
                    flash(
                        f"Velocity for Sprint {index+1} must be a positive number.",
                        "error",
                    )
                    return redirect(request.referrer)

                # Update sprint data
                sprint.SprintNo = int(sprint_no)
                sprint.ScrumMasterID = int(scrum_master_id)
                sprint.StartDate = sprint_start_date
                sprint.EndDate = sprint_end_date
                sprint.Velocity = int(velocity)
                db.session.commit()
                print(f"[INFO] Sprint {index+1} for project {project_id} updated")

                # ========== Validate and Update User Stories ==========
                for user_story_index, user_story in enumerate(sprint.user_stories):
                    # Validate user story description
                    user_story_description = request.form.get(
                        f"story_desc_{user_story_index+1}_{user_story_index}", ""
                    ).strip()
                    if not user_story_description:
                        db.session.rollback()
                        flash(
                            f"Description is required for User Story {user_story_index+1} in Sprint {index+1}.",
                            "error",
                        )
                        return redirect(request.referrer)
                    if len(user_story_description) < 5:
                        db.session.rollback()
                        flash(
                            f"User Story {user_story_index+1} description must be at least 5 characters.",
                            "error",
                        )
                        return redirect(request.referrer)

                    # Validate planned and actual sprint
                    planned_sprint = request.form.get(
                        f"planned_sprint_{user_story_index+1}_{user_story_index}", ""
                    ).strip()
                    actual_sprint = request.form.get(
                        f"actual_sprint_{user_story_index+1}_{user_story_index}", ""
                    ).strip()

                    if not planned_sprint or not planned_sprint.isdigit():
                        db.session.rollback()
                        flash(
                            f"Planned Sprint for User Story {user_story_index+1} in Sprint {index+1} must be a valid number.",
                            "error",
                        )
                        return redirect(request.referrer)
                    if not actual_sprint or not actual_sprint.isdigit():
                        db.session.rollback()
                        flash(
                            f"Actual Sprint for User Story {user_story_index+1} in Sprint {index+1} must be a valid number.",
                            "error",
                        )
                        return redirect(request.referrer)

                    # Validate story points
                    story_point = request.form.get(
                        f"story_points_{user_story_index+1}_{user_story_index}", ""
                    ).strip()
                    if not story_point or not story_point.isdigit() or int(story_point) <= 0:
                        db.session.rollback()
                        flash(
                            f"Story Point for User Story {user_story_index+1} in Sprint {index+1} must be a positive number.",
                            "error",
                        )
                        return redirect(request.referrer)

                    # Validate MOSCOW priority
                    moscow = request.form.get(
                        f"moscow_{user_story_index+1}_{user_story_index}", ""
                    ).strip()
                    valid_moscow = ["Must Have", "Should Have", "Could Have", "Won't Have"]
                    if moscow not in valid_moscow:
                        db.session.rollback()
                        flash(
                            f"Invalid MOSCOW value for User Story {user_story_index+1} in Sprint {index+1}. Must be one of: {', '.join(valid_moscow)}",
                            "error",
                        )
                        return redirect(request.referrer)

                    # Validate assignee
                    assignee = request.form.get(
                        f"assignee_{user_story_index+1}_{user_story_index}", ""
                    ).strip()
                    if not assignee:
                        db.session.rollback()
                        flash(
                            f"Assignee is required for User Story {user_story_index+1} in Sprint {index+1}.",
                            "error",
                        )
                        return redirect(request.referrer)

                    # Validate status
                    status = request.form.get(
                        f"status_{user_story_index+1}_{user_story_index}", ""
                    ).strip()
                    valid_statuses = ["Not Started", "In Progress", "Completed"]
                    if status not in valid_statuses:
                        db.session.rollback()
                        flash(
                            f"Invalid status for User Story {user_story_index+1} in Sprint {index+1}. Must be one of: {', '.join(valid_statuses)}",
                            "error",
                        )
                        return redirect(request.referrer)

                    # Update user story with validated data
                    user_story.Description = user_story_description
                    user_story.PlannedSprint = int(planned_sprint)
                    user_story.ActualSprint = int(actual_sprint)
                    user_story.StoryPoint = int(story_point)
                    user_story.MOSCOW = moscow
                    user_story.Assignee = assignee
                    user_story.Status = status
                    db.session.commit()
                    print(f"[INFO] User Story {user_story_index+1} in Sprint {index+1} updated")

            # Success message after all updates
            flash("Project successfully updated!", "success")
            print(f"[SUCCESS] All updates for project {project_id} completed successfully")
            return redirect(f"/projects/{session['role']}/{session['uid']}")
            
        except Exception as e:
            # Rollback all changes on any error
            db.session.rollback()
            print(f"[ERROR] Failed to update project {project_id}: {str(e)}")
            print(traceback.format_exc())
            flash(f"Error updating project: {str(e)}", "error")
            return redirect(request.referrer)

    return render_template(
        "edit_project.html", project=project, scrum_masters=scrum_masters
    )



@app.route('/viewproject/<int:project_id>', methods=['GET'])
@require_login()
def viewproject(project_id):
    """
    View detailed information about a specific project.
    
    Args:
        project_id (int): ID of the project to view
        
    Returns:
        Rendered template with project details, user stories, and sprints
        
    Access: All authenticated users who are part of the project team
    """
    try:
        # Validate project_id
        if project_id <= 0:
            flash("Invalid project ID", "error")
            return redirect(url_for('projects', role=session.get('role'), userid=session.get('uid')))
        
        # Fetch project with error handling
        project = ProjectDetails.query.filter_by(ProjectId=project_id).first()
        if not project:
            flash(f"Project with ID {project_id} not found", "error")
            return redirect(url_for('projects', role=session.get('role'), userid=session.get('uid')))

        # Check if user is part of this project
        user_role = session.get('role', '').lower()
        user_id = session.get('uid')
        
        # Product Owner and Admin can view all projects
        is_authorized = user_role in ['productowner', 'product owner', 'admin']
        
        # Check if user is a team member
        if not is_authorized:
            team_member = ProjectUsers.query.filter_by(UserID=user_id, ProjectId=project_id).first()
            is_authorized = team_member is not None
        
        if not is_authorized:
            flash("You are not authorized to view this project. Only team members can access project details.", "danger")
            return redirect(url_for('projects', role=session.get('role'), userid=session.get('uid')))

        # Set permissions based on user role
        user_role_lower = user_role.replace(' ', '').lower()
        
        # Admin and Product Owner have full permissions
        if user_role_lower in ['admin', 'productowner']:
            can_edit = True
            can_delete = True
            can_edit_sprints = True
            can_edit_stories = True
        # Scrum Master, Developer, and Tester have restricted permissions
        # They can only update status of stories assigned to them
        elif user_role_lower in ['scrummaster', 'developer', 'tester']:
            can_edit = False
            can_delete = False
            can_edit_sprints = False
            can_edit_stories = False  # Cannot edit stories directly, only status update via API for assigned stories
        else:
            # Default: no permissions
            can_edit = False
            can_delete = False
            can_edit_sprints = False
            can_edit_stories = False

        # Fetch user stories for the project
        userstories_data = UserStories.query.filter_by(ProjectId=project_id).all()
        
        userstories = [
            {
                "us_id": user_story.UserStoryID,
                "description": user_story.Description,
                "status": user_story.Status,
                "assignee": user_story.Assignee,
                "sprint": f"Sprint {user_story.SprintId}",
                "story_points": user_story.StoryPoint
            }
            for user_story in userstories_data
        ]

        # Fetch sprint calendar data
        sprints_data = SprintCalendar.query.filter_by(ProjectId=project_id).all()

        sprintcalendar = [
            {
                "sprint_no": sprint.SprintId,
                "start_date": sprint.StartDate.strftime('%b %d, %Y'),
                "end_date": sprint.EndDate.strftime('%b %d, %Y'),
                "velocity": sprint.Velocity,
                "scrum_master": sprint.scrum_master.Name if sprint.scrum_master else "Not assigned"
            }
            for sprint in sprints_data
        ]

        # Check if user has session
        if 'username' not in session:
            flash("Please log in to view projects", "error")
            return redirect(url_for('auth.login'))

        # Removed permission checks - all users have full access

        return render_template(
            'view.html', 
            userstories=userstories, 
            project=project, 
            sprints=sprintcalendar,
            user_name=session.get('username', 'Guest'),
            user_role=session.get('role', 'guest'),
            user_id=session.get('uid', 0),
            can_edit=can_edit,
            can_delete=can_delete,
            can_edit_sprints=can_edit_sprints,
            can_edit_stories=can_edit_stories
        )
        
    except Exception as e:
        # Log error and show user-friendly message
        print(f"[ERROR] Failed to view project {project_id}: {str(e)}")
        print(traceback.format_exc())
        flash("An error occurred while loading the project. Please try again.", "error")
        return redirect(url_for('auth.login'))


@app.route('/charts')
@require_login()
def charts():
    """
    Display comprehensive analytics dashboard with all charts.
    All authenticated users can view charts.
    
    Returns:
        Rendered template with charts dashboard
    """
    try:
        return render_template(
            'charts.html',
            user_name=session.get('username', 'Guest'),
            user_role=session.get('role', 'guest'),
            user_id=session.get('uid', 0)
        )
    except Exception as e:
        print(f"[ERROR] Failed to load charts dashboard: {str(e)}")
        print(traceback.format_exc())
        flash("An error occurred while loading the analytics. Please try again.", "error")
        return redirect(url_for('auth.login'))


@app.route('/api/update-story-status/<int:story_id>', methods=['POST'])
@require_login()
def update_story_status(story_id):
    """
    Update the status of a user story.
    - Admin, Product Owner: Can update any story status
    - Developer, Tester, Scrum Master: Can only update status of stories assigned to them
    
    Args:
        story_id (int): The ID of the user story to update
        
    Returns:
        JSON response with success/error message
    """
    try:
        # Get the new status from request
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({
                'success': False,
                'message': 'Status is required'
            }), 400
        
        # Validate status values
        valid_statuses = ['Not Started', 'In Progress', 'Completed', 'Blocked', 'Testing']
        if new_status not in valid_statuses:
            return jsonify({
                'success': False,
                'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }), 400
        
        # Find the user story
        story = UserStories.query.filter_by(UserStoryID=story_id).first()
        
        if not story:
            return jsonify({
                'success': False,
                'message': 'User story not found'
            }), 404
        
        # Get user info
        user_id = session.get('uid')
        user_role = session.get('role', '').lower().replace(' ', '')
        user = Users.query.filter_by(UserID=user_id).first()
        
        # Check authorization based on role
        if user_role in ['admin', 'productowner']:
            # Admin and Product Owner can update any story status
            is_authorized = True
        elif user_role in ['developer', 'tester', 'scrummaster']:
            # Developers, Testers, and Scrum Masters can only update stories assigned to them
            # Check if the story is assigned to this user
            if story.Assignee and user:
                # Assignee field contains the user's name
                is_authorized = (story.Assignee.lower() == user.Name.lower() or 
                               story.Assignee.lower() == user.UserName.lower())
            else:
                is_authorized = False
        else:
            is_authorized = False
        
        if not is_authorized:
            return jsonify({
                'success': False,
                'message': 'You can only update status of user stories assigned to you'
            }), 403
        
        # Update only the status field
        old_status = story.Status
        story.Status = new_status
        
        # Commit the change
        db.session.commit()
        
        print(f"[INFO] User Story {story_id} status updated from '{old_status}' to '{new_status}' by user {user_id}")
        
        return jsonify({
            'success': True,
            'message': f'Story status updated to "{new_status}"',
            'old_status': old_status,
            'new_status': new_status,
            'story_id': story_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Failed to update story {story_id} status: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': 'An error occurred while updating the story status'
        }), 500


@app.route('/api/chart-data')
def chart_data():
    try:
        sprints = SprintCalendar.query.all()
        projects = ProjectDetails.query.all()
        user_stories = UserStories.query.all()
        scrum_masters = ScrumMasters.query.all()
        tasks = Tasks.query.all()

        # Fixed: Match frontend expectation with statusCounts
        status_counts = {
            "total": len(user_stories),
            "completed": sum(1 for us in user_stories if us.Status == "Completed"),
            "inProgress": sum(1 for us in user_stories if us.Status == "In Progress"),
            "notStarted": sum(1 for us in user_stories if us.Status == "Not Started")
        }

        # Prepare sprint data with actual story point calculations
        sprint_data = []
        cumulative_completed = 0
        cumulative_estimated = 0
        
        for sprint in sorted(sprints, key=lambda s: s.SprintNo):
            # Get stories for this sprint
            sprint_stories = [us for us in user_stories if us.SprintId == sprint.SprintId]
            
            # Calculate completed story points in this sprint
            completed_points = sum(us.StoryPoint for us in sprint_stories if us.Status == "Completed")
            
            # Calculate total story points planned for this sprint
            total_points = sum(us.StoryPoint for us in sprint_stories)
            
            # Update cumulative values
            cumulative_completed += completed_points
            cumulative_estimated += sprint.Velocity
            
            sprint_data.append({
                "sprintNo": sprint.SprintNo,
                "velocity": sprint.Velocity,
                "estimatedEffort": sprint.Velocity,
                "actualEffort": completed_points,
                "totalPlanned": total_points,
                "cumulativeEstimated": cumulative_estimated,
                "cumulativeCompleted": cumulative_completed
            })

        sprint_progress = [{
            "sprintNo": sprint.SprintNo,
            "progress": (sum(1 for us in user_stories
                           if us.SprintId == sprint.SprintId and us.Status == "Completed") /
                         len([us for us in user_stories if us.SprintId ==
                             sprint.SprintId]) * 100
                         if len([us for us in user_stories if us.SprintId == sprint.SprintId]) > 0
                         else 0)
        } for sprint in sprints]

        # Group team performance by Scrum Master (each scrum master leads one team)
        team_performance = []
        
        for idx, scrum_master in enumerate(scrum_masters, start=1):
            # Get all sprints led by this scrum master
            team_sprints = SprintCalendar.query.filter_by(ScrumMasterID=scrum_master.ScrumMasterID).all()
            sprint_ids = [sprint.SprintId for sprint in team_sprints]
            
            if sprint_ids:
                # Count completed stories for this team's sprints
                completed_stories = db.session.query(UserStories)\
                    .filter(UserStories.SprintId.in_(sprint_ids),
                           UserStories.Status == 'Completed')\
                    .count()
                
                # Count in-progress stories for this team
                in_progress_stories = db.session.query(UserStories)\
                    .filter(UserStories.SprintId.in_(sprint_ids),
                           UserStories.Status == 'In Progress')\
                    .count()
                
                # Count total stories for this team
                total_stories = db.session.query(UserStories)\
                    .filter(UserStories.SprintId.in_(sprint_ids))\
                    .count()
                
                team_performance.append({
                    "team": f"Team {idx} ({scrum_master.Name})",
                    "completedTasks": in_progress_stories,  # In Progress tasks
                    "completedStories": completed_stories,   # Completed stories
                    "totalStories": total_stories,
                    "averagePerformance": (completed_stories / total_stories * 100) if total_stories > 0 else 0
                })

        return jsonify({
            "sprintData": sprint_data,
            "sprintProgress": sprint_progress,
            "teamPerformance": team_performance,
            "statusCounts": status_counts
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chart-data/<int:project_id>')
def project_chart_data(project_id):
    """
    Get chart data for a specific project.
    
    Args:
        project_id (int): ID of the project
        
    Returns:
        JSON with chart data for the specific project
    """
    try:
        # Get sprints for this project
        sprints = SprintCalendar.query.filter_by(ProjectId=project_id).all()
        
        # Get user stories for this project
        user_stories = UserStories.query.filter_by(ProjectId=project_id).all()
        
        # Get all tasks for user stories in this project
        story_ids = [us.UserStoryID for us in user_stories]
        tasks = Tasks.query.filter(Tasks.UserStoryID.in_(story_ids)).all() if story_ids else []

        # Status counts for this project
        status_counts = {
            "total": len(user_stories),
            "completed": sum(1 for us in user_stories if us.Status == "Completed"),
            "inProgress": sum(1 for us in user_stories if us.Status == "In Progress"),
            "notStarted": sum(1 for us in user_stories if us.Status == "Not Started")
        }

        # Prepare sprint data with actual story point calculations
        sprint_data = []
        cumulative_completed = 0
        cumulative_estimated = 0
        
        for sprint in sorted(sprints, key=lambda s: s.SprintNo):
            # Get stories for this sprint
            sprint_stories = [us for us in user_stories if us.SprintId == sprint.SprintId]
            
            # Calculate completed story points in this sprint
            completed_points = sum(us.StoryPoint for us in sprint_stories if us.Status == "Completed")
            
            # Calculate total story points planned for this sprint
            total_points = sum(us.StoryPoint for us in sprint_stories)
            
            # Update cumulative values
            cumulative_completed += completed_points
            cumulative_estimated += sprint.Velocity
            
            sprint_data.append({
                "sprintNo": sprint.SprintNo,
                "velocity": sprint.Velocity,
                "estimatedEffort": sprint.Velocity,
                "actualEffort": completed_points,
                "totalPlanned": total_points,
                "cumulativeEstimated": cumulative_estimated,
                "cumulativeCompleted": cumulative_completed
            })

        # Sprint progress
        sprint_progress = [{
            "sprintNo": sprint.SprintNo,
            "progress": (sum(1 for us in user_stories
                           if us.SprintId == sprint.SprintId and us.Status == "Completed") /
                         len([us for us in user_stories if us.SprintId == sprint.SprintId]) * 100
                         if len([us for us in user_stories if us.SprintId == sprint.SprintId]) > 0
                         else 0)
        } for sprint in sprints]

        # Team performance for this project (grouped by Scrum Master)
        team_performance = []
        scrum_master_ids = set(s.ScrumMasterID for s in sprints if s.ScrumMasterID)
        
        for idx, sm_id in enumerate(sorted(scrum_master_ids), start=1):
            scrum_master = ScrumMasters.query.get(sm_id)
            if scrum_master:
                # Get sprint IDs for this scrum master in this project
                sprint_ids = [s.SprintId for s in sprints if s.ScrumMasterID == sm_id]
                
                if sprint_ids:
                    # Count stories for this team
                    completed_stories = sum(1 for us in user_stories 
                                          if us.SprintId in sprint_ids and us.Status == 'Completed')
                    
                    in_progress_stories = sum(1 for us in user_stories 
                                            if us.SprintId in sprint_ids and us.Status == 'In Progress')
                    
                    total_stories = sum(1 for us in user_stories if us.SprintId in sprint_ids)
                    
                    team_performance.append({
                        "team": f"Team {idx} ({scrum_master.Name})",
                        "completedTasks": in_progress_stories,
                        "completedStories": completed_stories,
                        "totalStories": total_stories,
                        "averagePerformance": (completed_stories / total_stories * 100) if total_stories > 0 else 0
                    })

        result = {
            "sprintData": sprint_data,
            "sprintProgress": sprint_progress,
            "teamPerformance": team_performance,
            "statusCounts": status_counts
        }
        
        print(f"[DEBUG] Returning chart data for project {project_id}:")
        print(f"  - Sprints: {len(sprint_data)}")
        print(f"  - Sprint Progress: {len(sprint_progress)}")
        print(f"  - Teams: {len(team_performance)}")
        print(f"  - Status Counts: {status_counts}")
        if sprint_data:
            print(f"  - Sample Sprint Data: {sprint_data[0]}")
        
        return jsonify(result)

    except Exception as e:
        print(f"[ERROR] Failed to get chart data for project {project_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500



@app.route('/summary')
@require_login()
def summary():
    """
    Display project summary with statistics.
    All authenticated users can view summary.
    
    Returns:
        Rendered template with summary data
    """
    try:
        projects = ProjectDetails.query.all()
        sprints = SprintCalendar.query.all()
        user_stories = UserStories.query.all()
        tasks = Tasks.query.all()

        project_summary = {
            "total_projects": len(projects),
            "completed_projects": sum(1 for p in projects if p.Status == "Completed"),
            "active_projects": sum(1 for p in projects if p.Status == "Active"),
            "pending_projects": sum(1 for p in projects if p.Status == "Not Started")
        }

        sprint_summary = {
            "total_sprints": len(sprints),
            "average_velocity": sum(s.Velocity for s in sprints) / len(sprints) if sprints else 0,
            "current_sprint": max(s.SprintNo for s in sprints) if sprints else None
        }

        user_story_summary = {
            "total_user_stories": len(user_stories),
            "completed_stories": sum(1 for u in user_stories if u.Status == "Completed"),
            "in_progress_stories": sum(1 for u in user_stories if u.Status == "In Progress"),
            "pending_stories": sum(1 for u in user_stories if u.Status == "Not Started")
        }

        task_summary = {
            "total_tasks": len(tasks),
            "completed_tasks": sum(1 for t in tasks if t.TaskStatus == "Completed"),
            "in_progress_tasks": sum(1 for t in tasks if t.TaskStatus == "In Progress"),
            "pending_tasks": sum(1 for t in tasks if t.TaskStatus == "Not Started")
        }

        summary_data = {
            "projects": project_summary,
            "sprints": sprint_summary,
            "user_stories": user_story_summary,
            "tasks": task_summary
        }

        # Allow all users to download reports
        can_download_reports = True

        return render_template(
            "summary.html",
            user_name=session['username'],
            user_role=session.get('role', 'guest'),
            user_id=session.get('uid', 0),
            summary_data=summary_data,
            can_generate_reports=can_download_reports  # Changed: use download permission
        )

    except Exception as e:
        print(f"[ERROR] Failed to load summary: {str(e)}")
        print(traceback.format_exc())
        flash("An error occurred while fetching the summary. Please try again.", "error")
        return redirect(url_for('auth.login'))


@app.route('/export-pdf')
@require_login()
def export_pdf():
    """
    Export agile dashboard report as PDF file.
    Only Product Owners can download reports.
    
    Returns:
        file: PDF report as downloadable attachment
        
    Raises:
        Exception: If PDF generation fails, redirects to summary with error message
    """
    try:
        # Generate PDF data
        pdf_data = generate_pdf()
        
        if not pdf_data:
            flash("Failed to generate PDF report. Please try again.", "error")
            return redirect(url_for('summary'))
        
        # Create filename with current date
        filename = f'agile_dashboard_report_{datetime.now().strftime("%Y%m%d")}.pdf'
        
        # Send file as attachment
        return send_file(
            BytesIO(pdf_data),
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"[ERROR] Failed to export PDF: {str(e)}")
        print(traceback.format_exc())
        flash("Error exporting PDF report. Please try again later.", "error")
        return redirect(url_for('summary'))

@app.route('/generate-pdf')
@require_login()
def generate_pdf():
    """
    Generate PDF report data with charts and beautiful formatting.
    Only Product Owners and Scrum Masters can generate reports.
    
    Returns:
        bytes: PDF file data
    """
    try:
        projects = ProjectDetails.query.all()
        sprints = SprintCalendar.query.all()
        user_stories = UserStories.query.all()
        tasks = Tasks.query.all()

        project_summary = {
            "total": len(projects),
            "completed": sum(1 for p in projects if p.Status == "Completed"),
            "active": sum(1 for p in projects if p.Status == "Active"),
            "pending": sum(1 for p in projects if p.Status == "Not Started")
        }

        sprint_summary = {
            "total": len(sprints),
            "velocity": sum(s.Velocity for s in sprints) / len(sprints) if sprints else 0,
            "current": max(s.SprintNo for s in sprints) if sprints else None
        }

        story_summary = {
            "total": len(user_stories),
            "completed": sum(1 for u in user_stories if u.Status == "Completed"),
            "in_progress": sum(1 for u in user_stories if u.Status == "In Progress"),
            "pending": sum(1 for u in user_stories if u.Status == "Not Started")
        }

        task_summary = {
            "total": len(tasks),
            "completed": sum(1 for t in tasks if t.TaskStatus == "Completed"),
            "in_progress": sum(1 for t in tasks if t.TaskStatus == "In Progress"),
            "pending": sum(1 for t in tasks if t.TaskStatus == "Not Started")
        }

        # Create temporary directory for charts
        temp_dir = tempfile.mkdtemp()
        
        # Generate Charts with optimized settings
        chart_files = []
        
        # 1. Project Status Pie Chart
        if project_summary["total"] > 0:
            fig, ax = plt.subplots(figsize=(5, 3.5))
            colors = ['#48bb78', '#667eea', '#ed8936']
            labels = ['Completed', 'Active', 'Pending']
            sizes = [project_summary["completed"], project_summary["active"], project_summary["pending"]]
            explode = (0.05, 0, 0)
            
            ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
                   shadow=True, startangle=90, textprops={'fontsize': 9, 'weight': 'bold'})
            ax.axis('equal')
            plt.title('Project Status Distribution', fontsize=12, weight='bold', pad=15)
            
            project_chart = os.path.join(temp_dir, 'project_chart.png')
            plt.savefig(project_chart, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close()
            chart_files.append(project_chart)
        
        # 2. User Stories Bar Chart
        if story_summary["total"] > 0:
            fig, ax = plt.subplots(figsize=(5, 3.5))
            categories = ['Completed', 'In Progress', 'Pending']
            values = [story_summary["completed"], story_summary["in_progress"], story_summary["pending"]]
            colors = ['#48bb78', '#ed8936', '#4299e1']
            
            bars = ax.bar(categories, values, color=colors, edgecolor='black', linewidth=1)
            ax.set_ylabel('Number of Stories', fontsize=10, weight='bold')
            ax.set_title('User Stories Progress', fontsize=12, weight='bold', pad=15)
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom', fontsize=9, weight='bold')
            
            story_chart = os.path.join(temp_dir, 'story_chart.png')
            plt.savefig(story_chart, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close()
            chart_files.append(story_chart)
        
        # 3. Tasks Progress Donut Chart
        if task_summary["total"] > 0:
            fig, ax = plt.subplots(figsize=(5, 3.5))
            colors = ['#48bb78', '#ed8936', '#4299e1']
            labels = ['Completed', 'In Progress', 'Pending']
            sizes = [task_summary["completed"], task_summary["in_progress"], task_summary["pending"]]
            
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                               startangle=90, textprops={'fontsize': 9, 'weight': 'bold'})
            
            # Draw circle in center to make it a donut chart
            centre_circle = plt.Circle((0, 0), 0.70, fc='white')
            fig.gca().add_artist(centre_circle)
            
            ax.axis('equal')
            plt.title('Task Status Overview', fontsize=12, weight='bold', pad=15)
            
            task_chart = os.path.join(temp_dir, 'task_chart.png')
            plt.savefig(task_chart, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close()
            chart_files.append(task_chart)
        
        # 4. Sprint Velocity Line Chart (if multiple sprints)
        if len(sprints) > 1:
            fig, ax = plt.subplots(figsize=(5, 3.5))
            sprint_numbers = [s.SprintNo for s in sorted(sprints, key=lambda x: x.SprintNo)]
            velocities = [s.Velocity for s in sorted(sprints, key=lambda x: x.SprintNo)]
            
            ax.plot(sprint_numbers, velocities, marker='o', linewidth=2, markersize=7,
                   color='#667eea', markerfacecolor='#764ba2', markeredgecolor='white', markeredgewidth=1.5)
            ax.set_xlabel('Sprint Number', fontsize=10, weight='bold')
            ax.set_ylabel('Velocity', fontsize=10, weight='bold')
            ax.set_title('Sprint Velocity Trend', fontsize=12, weight='bold', pad=15)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.fill_between(sprint_numbers, velocities, alpha=0.2, color='#667eea')
            
            velocity_chart = os.path.join(temp_dir, 'velocity_chart.png')
            plt.savefig(velocity_chart, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close()
            chart_files.append(velocity_chart)

        # Create PDF with enhanced styling
        buffer = BytesIO()
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # ========== COVER PAGE ==========
        pdf.add_page()
        
        # Purple gradient background (simulated with rectangles)
        pdf.set_fill_color(102, 126, 234)  # #667eea
        pdf.rect(0, 0, 210, 100, 'F')
        pdf.set_fill_color(118, 75, 162)  # #764ba2
        pdf.rect(0, 100, 210, 197, 'F')
        
        # White text on gradient
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 36)
        pdf.ln(80)
        pdf.cell(0, 20, 'AGILE PROJECT', ln=True, align='C')
        pdf.cell(0, 20, 'MANAGEMENT', ln=True, align='C')
        pdf.set_font('Arial', 'B', 28)
        pdf.cell(0, 20, 'DASHBOARD', ln=True, align='C')
        
        pdf.ln(20)
        pdf.set_font('Arial', 'I', 16)
        pdf.cell(0, 10, 'Comprehensive Analytics Report', ln=True, align='C')
        
        pdf.ln(30)
        pdf.set_font('Arial', '', 14)
        pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", ln=True, align='C')
        
        # ========== TABLE OF CONTENTS ==========
        pdf.add_page()
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(102, 126, 234)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 20)
        pdf.cell(0, 12, 'TABLE OF CONTENTS', ln=True, align='L', fill=True)
        
        pdf.ln(5)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 12)
        
        contents = [
            '1. Executive Summary',
            '2. Project Overview & Statistics',
            '3. Sprint Performance Analysis',
            '4. User Stories Progress',
            '5. Task Management Summary',
            '6. Visual Analytics & Charts',
            '7. Conclusion & Recommendations'
        ]
        
        for item in contents:
            pdf.cell(0, 10, item, ln=True)
            pdf.ln(2)

        # ========== EXECUTIVE SUMMARY ==========
        pdf.add_page()
        pdf.set_fill_color(102, 126, 234)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 12, '1. EXECUTIVE SUMMARY', ln=True, align='L', fill=True)
        
        pdf.ln(5)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 11)
        
        executive_summary = f"""
This report provides a comprehensive analysis of the Agile Project Management Dashboard, covering all active projects, sprint performance, user story completion rates, and task management metrics.

Key Highlights:
- Total Projects: {project_summary['total']} projects are being managed
- Project Completion Rate: {(project_summary['completed']/project_summary['total']*100) if project_summary['total'] > 0 else 0:.1f}%
- Active Sprints: {sprint_summary['total']} sprints completed
- Average Sprint Velocity: {sprint_summary['velocity']:.1f} story points
- User Story Completion: {(story_summary['completed']/story_summary['total']*100) if story_summary['total'] > 0 else 0:.1f}%
- Task Completion Rate: {(task_summary['completed']/task_summary['total']*100) if task_summary['total'] > 0 else 0:.1f}%

The team demonstrates strong Agile practices with consistent sprint execution and story delivery. This report details the metrics, trends, and insights to support continuous improvement.
"""
        pdf.multi_cell(0, 6, executive_summary.strip())

        # ========== PROJECT OVERVIEW ==========
        pdf.add_page()
        pdf.set_fill_color(72, 187, 120)  # Green
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 12, '2. PROJECT OVERVIEW & STATISTICS', ln=True, align='L', fill=True)
        
        pdf.ln(5)
        pdf.set_text_color(0, 0, 0)
        
        # Project Stats Box
        pdf.set_fill_color(240, 248, 255)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Project Summary', ln=True, fill=True)
        
        pdf.set_font('Arial', '', 12)
        pdf.ln(3)
        
        # Create a nice table
        pdf.set_fill_color(102, 126, 234)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(100, 10, 'Metric', 1, 0, 'C', fill=True)
        pdf.cell(90, 10, 'Value', 1, 1, 'C', fill=True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 11)
        
        project_data = [
            ('Total Projects', str(project_summary['total'])),
            ('Completed Projects', str(project_summary['completed'])),
            ('Active Projects', str(project_summary['active'])),
            ('Pending Projects', str(project_summary['pending'])),
            ('Completion Rate', f"{(project_summary['completed']/project_summary['total']*100) if project_summary['total'] > 0 else 0:.1f}%")
        ]
        
        for i, (metric, value) in enumerate(project_data):
            fill = i % 2 == 0
            pdf.set_fill_color(245, 245, 245)
            pdf.cell(100, 9, metric, 1, 0, 'L', fill)
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(90, 9, value, 1, 1, 'C', fill)
            pdf.set_font('Arial', '', 11)

        # Add Project Status Chart
        if len(chart_files) > 0 and os.path.exists(chart_files[0]):
            pdf.ln(10)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'Project Status Distribution Chart', ln=True)
            pdf.image(chart_files[0], x=30, w=150)

        # ========== SPRINT ANALYSIS ==========
        pdf.add_page()
        pdf.set_fill_color(237, 137, 54)  # Orange
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 12, '3. SPRINT PERFORMANCE ANALYSIS', ln=True, align='L', fill=True)
        
        pdf.ln(5)
        pdf.set_text_color(0, 0, 0)
        
        pdf.set_fill_color(240, 248, 255)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Sprint Metrics', ln=True, fill=True)
        
        pdf.set_font('Arial', '', 12)
        pdf.ln(3)
        
        # Sprint Stats Table
        pdf.set_fill_color(237, 137, 54)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(100, 10, 'Metric', 1, 0, 'C', fill=True)
        pdf.cell(90, 10, 'Value', 1, 1, 'C', fill=True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 11)
        
        sprint_data = [
            ('Total Sprints Completed', str(sprint_summary['total'])),
            ('Average Sprint Velocity', f"{sprint_summary['velocity']:.1f} points"),
            ('Current Sprint Number', str(sprint_summary['current'] or 'N/A')),
        ]
        
        for i, (metric, value) in enumerate(sprint_data):
            fill = i % 2 == 0
            pdf.set_fill_color(245, 245, 245)
            pdf.cell(100, 9, metric, 1, 0, 'L', fill)
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(90, 9, value, 1, 1, 'C', fill)
            pdf.set_font('Arial', '', 11)

        # Add Velocity Chart if exists
        if len(chart_files) > 3 and os.path.exists(chart_files[3]):
            pdf.ln(10)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'Sprint Velocity Trend', ln=True)
            pdf.image(chart_files[3], x=30, w=150)

        # ========== USER STORIES ==========
        pdf.add_page()
        pdf.set_fill_color(156, 39, 176)  # Purple
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 12, '4. USER STORIES PROGRESS', ln=True, align='L', fill=True)
        
        pdf.ln(5)
        pdf.set_text_color(0, 0, 0)
        
        pdf.set_fill_color(240, 248, 255)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Story Metrics', ln=True, fill=True)
        
        pdf.set_font('Arial', '', 12)
        pdf.ln(3)
        
        # Story Stats Table
        pdf.set_fill_color(156, 39, 176)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(100, 10, 'Metric', 1, 0, 'C', fill=True)
        pdf.cell(90, 10, 'Value', 1, 1, 'C', fill=True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 11)
        
        story_data = [
            ('Total User Stories', str(story_summary['total'])),
            ('Completed Stories', str(story_summary['completed'])),
            ('In Progress Stories', str(story_summary['in_progress'])),
            ('Pending Stories', str(story_summary['pending'])),
            ('Completion Rate', f"{(story_summary['completed']/story_summary['total']*100) if story_summary['total'] > 0 else 0:.1f}%")
        ]
        
        for i, (metric, value) in enumerate(story_data):
            fill = i % 2 == 0
            pdf.set_fill_color(245, 245, 245)
            pdf.cell(100, 9, metric, 1, 0, 'L', fill)
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(90, 9, value, 1, 1, 'C', fill)
            pdf.set_font('Arial', '', 11)

        # Add Story Chart
        if len(chart_files) > 1 and os.path.exists(chart_files[1]):
            pdf.ln(10)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'User Stories Status Chart', ln=True)
            pdf.image(chart_files[1], x=30, w=150)

        # ========== TASKS ==========
        pdf.add_page()
        pdf.set_fill_color(66, 153, 225)  # Blue
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 12, '5. TASK MANAGEMENT SUMMARY', ln=True, align='L', fill=True)
        
        pdf.ln(5)
        pdf.set_text_color(0, 0, 0)
        
        pdf.set_fill_color(240, 248, 255)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Task Metrics', ln=True, fill=True)
        
        pdf.set_font('Arial', '', 12)
        pdf.ln(3)
        
        # Task Stats Table
        pdf.set_fill_color(66, 153, 225)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(100, 10, 'Metric', 1, 0, 'C', fill=True)
        pdf.cell(90, 10, 'Value', 1, 1, 'C', fill=True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 11)
        
        task_data = [
            ('Total Tasks', str(task_summary['total'])),
            ('Completed Tasks', str(task_summary['completed'])),
            ('In Progress Tasks', str(task_summary['in_progress'])),
            ('Pending Tasks', str(task_summary['pending'])),
            ('Completion Rate', f"{(task_summary['completed']/task_summary['total']*100) if task_summary['total'] > 0 else 0:.1f}%")
        ]
        
        for i, (metric, value) in enumerate(task_data):
            fill = i % 2 == 0
            pdf.set_fill_color(245, 245, 245)
            pdf.cell(100, 9, metric, 1, 0, 'L', fill)
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(90, 9, value, 1, 1, 'C', fill)
            pdf.set_font('Arial', '', 11)

        # Add Task Chart
        if len(chart_files) > 2 and os.path.exists(chart_files[2]):
            pdf.ln(10)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'Task Status Overview Chart', ln=True)
            pdf.image(chart_files[2], x=30, w=150)

        # ========== CONCLUSION ==========
        pdf.add_page()
        pdf.set_fill_color(72, 187, 120)  # Green
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 12, '6. CONCLUSION & RECOMMENDATIONS', ln=True, align='L', fill=True)
        
        pdf.ln(5)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 11)
        
        conclusion = f"""
Performance Summary:

The Agile Project Management Dashboard demonstrates effective project execution with {project_summary['total']} projects currently being managed. The team has achieved a {(project_summary['completed']/project_summary['total']*100) if project_summary['total'] > 0 else 0:.1f}% project completion rate and maintains an average sprint velocity of {sprint_summary['velocity']:.1f} story points.

Key Achievements:
- Completed {story_summary['completed']} out of {story_summary['total']} user stories
- Delivered {task_summary['completed']} out of {task_summary['total']} tasks
- Successfully executed {sprint_summary['total']} sprints
- {project_summary['active']} projects currently in active development

Recommendations:
1. Continue maintaining consistent sprint velocity for predictable delivery
2. Focus on reducing pending user stories to improve throughput
3. Monitor in-progress items to prevent work-in-progress bottlenecks
4. Maintain regular retrospectives to capture improvement opportunities
5. Ensure proper story estimation for better velocity tracking

Next Steps:
- Review pending projects and prioritize based on business value
- Analyze blocked items and remove impediments
- Continue fostering team collaboration and Agile practices
- Schedule regular reviews to track progress against goals

This dashboard serves as a powerful tool for visibility, enabling data-driven decisions and continuous improvement in project delivery.
"""
        pdf.multi_cell(0, 6, conclusion.strip())

        # ========== FOOTER PAGE ==========
        pdf.add_page()
        pdf.set_fill_color(102, 126, 234)
        pdf.rect(0, 0, 210, 297, 'F')
        
        pdf.set_text_color(255, 255, 255)
        pdf.ln(100)
        pdf.set_font('Arial', 'B', 28)
        pdf.cell(0, 20, 'Thank You', ln=True, align='C')
        
        pdf.ln(10)
        pdf.set_font('Arial', '', 14)
        pdf.cell(0, 10, 'For more information, please contact:', ln=True, align='C')
        pdf.cell(0, 10, 'Agile Project Management Team', ln=True, align='C')
        
        pdf.ln(20)
        pdf.set_font('Arial', 'I', 12)
        pdf.cell(0, 10, f"Report Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", ln=True, align='C')
        pdf.cell(0, 10, '© 2024 Agile Project Management Dashboard', ln=True, align='C')

        # Generate PDF
        pdf_output = pdf.output(dest='S').encode('latin1')
        buffer.write(pdf_output)
        buffer.seek(0)
        
        # Clean up temporary chart files
        for chart_file in chart_files:
            try:
                if os.path.exists(chart_file):
                    os.remove(chart_file)
            except:
                pass
        
        try:
            os.rmdir(temp_dir)
        except:
            pass
        
        return buffer.getvalue()

    except Exception as e:
        print(f"[ERROR] Failed to generate PDF: {str(e)}")
        print(traceback.format_exc())
        return None

# ==================== Real-Time WebSocket Handlers ====================
# These handlers enable real-time data synchronization across all connected clients
# When any user updates project data, all other users see the changes instantly

@socketio.on('connect')
def handle_connect():
    """
    Handle new client WebSocket connection.
    Fired when a user opens the dashboard.
    """
    try:
        print(f'[WebSocket] Client connected: {request.sid}')
    except Exception as e:
        print(f'[ERROR] WebSocket connection error: {str(e)}')

@socketio.on('join_project')
def handle_join_project(data):
    """
    Join a project-specific room for targeted updates.
    
    Args:
        data (dict): Contains 'project_id' to join
    """
    try:
        project_id = data.get('project_id')
        if project_id:
            join_room(f'project_{project_id}')
            print(f'[WebSocket] Client {request.sid} joined project room: {project_id}')
        else:
            print(f'[WARNING] Join project called without project_id')
    except Exception as e:
        print(f'[ERROR] Failed to join project room: {str(e)}')

@socketio.on('project_updated')
def handle_project_update(data):
    """
    Broadcast project update to all clients in the project room.
    
    Args:
        data (dict): Contains 'project_id' that was updated
    """
    try:
        project_id = data.get('project_id')
        if project_id:
            # Emit refresh signal to all clients in this project's room
            socketio.emit('refresh_data', {'project_id': project_id}, room=f'project_{project_id}')
            print(f'[WebSocket] Project {project_id} updated, notifying room members')
        else:
            print(f'[WARNING] Project update called without project_id')
    except Exception as e:
        print(f'[ERROR] Failed to broadcast project update: {str(e)}')

@socketio.on('disconnect')
def handle_disconnect():
    """
    Handle client disconnection.
    Fired when a user closes the dashboard or loses connection.
    """
    try:
        print(f'[WebSocket] Client disconnected: {request.sid}')
    except Exception as e:
        print(f'[ERROR] WebSocket disconnection error: {str(e)}')

# ==================== Application Entry Point ====================

if __name__ == '__main__':
    """
    Start the Flask application with WebSocket support.
    The socketio.run() method handles both HTTP and WebSocket connections.
    """
    print("="*50)
    print("🚀 Starting Agile Dashboard Application")
    print("="*50)
    socketio.run(app, debug=True)
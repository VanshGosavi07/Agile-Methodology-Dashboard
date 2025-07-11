from flask import Flask, redirect, url_for, render_template, flash, jsonify, request, send_file, Response,session
from database import db 
import os
from datetime import datetime
import send_mail as sm
from fpdf import FPDF
import schedule
import time
from threading import Thread
from io import BytesIO
import traceback
# Import your models
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

# Import your blueprints
#from routers.team1 import login_bp, login_manager
from routers.team1 import login_bp, login_manager

app = Flask(__name__)
login_manager.init_app(app)
login_manager.login_view = "auth.login"


# Configurations
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "8BYkEfBA6O6donzWlSihBXox7C0sKR6b")
app.config["SESSION_COOKIE_NAME"] = "your_session_cookie_name"

# Database configuration for Vercel (use PostgreSQL in production, SQLite for development)
if os.environ.get('VERCEL_ENV'):
    # Production database (PostgreSQL or other cloud database)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL', 'sqlite:///global.db')
else:
    # Development database
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite:///{os.path.join(app.instance_path, 'global.db')}"
    )
    os.makedirs(app.instance_path, exist_ok=True)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# app.config["SQLALCHEMY_ECHO"] = True


# Initialize extensions
db.init_app(app)

# Register the auth blueprint with the url_prefix 'auth'
app.register_blueprint(login_bp, url_prefix="/auth")

# Create tables if necessary
with app.app_context():
    db.create_all()

# Schedule automated reports (disabled in production/Vercel environment)
def setup_scheduled_reports():
    """Setup scheduled reports - only for local development"""
    if not os.environ.get('VERCEL_ENV'):
        schedule.every().day.at("18:29").do(lambda: generate_scheduled_report("daily")
                                            if datetime.now().day != 1 and datetime.now().strftime('%A').lower() != "monday" else None)
        schedule.every().monday.at("00:00").do(
            lambda: generate_scheduled_report("weekly"))
        schedule.every().day.at("18:37").do(lambda: generate_scheduled_report(
            "monthly") if datetime.now().day == 1 else None)

        # Start the scheduler in a separate thread
        scheduler_thread = Thread(target=schedule_reports, daemon=True)
        scheduler_thread.start()
        print("Scheduled reports initialized for local development")


@app.route('/')
def new_home():
    return redirect(url_for('auth.login'))


user=''
@app.route("/projects/<role>/<int:userid>")
def projects(role,userid):
    projects_data = ProjectDetails.query.all()
    print(projects_data)
    total_projects = ProjectDetails.query.count()
    active_projects = ProjectDetails.query.filter_by(Status="Active").count()
    on_hold_projects = ProjectDetails.query.filter_by(Status="On Hold").count()
    user = Users.query.filter_by(UserID=userid).first().Name

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
        user_name=session['username'],
        role=role
    )


@app.route("/api/product_owners", methods=["GET"])
def get_product_owners():
    owners = ProductOwner.query.all()
    return jsonify(
        [{"id": owner.ProductOwnerId, "name": owner.Name} for owner in owners]
    )


@app.route("/api/scrum_masters", methods=["GET"])
def scrumMasters():
    smasters = ScrumMasters.query.all()
    return jsonify(
        [{"id": smaster.ScrumMasterID, "name": smaster.Name} for smaster in smasters]
    )


@app.route("/api/users", methods=["GET"])
def users():
    users = Users.query.all()
    return jsonify([{"id": user.UserID, "name": user.UserName} for user in users])


@app.route("/addproject")
def addproject():
    return render_template("addproject.html",user_name=session['username'],user_role=session['role'],user_id=session['uid'])


def get_all_scrum_masters():
    scrum_masters = ScrumMasters.query.all()  # Assuming ScrumMaster is your model
    return [{"id": sm.ScrumMasterID, "name": sm.Name} for sm in scrum_masters]


@app.route("/editproject/<int:project_id>", methods=["GET", "POST"])
def edit_project(project_id):
    if request.method == "GET":
        try:
            # Fetch project details
            project = ProjectDetails.query.filter_by(ProjectId=project_id).first()
            scrum_masters = get_all_scrum_masters()
            print(scrum_masters)
            if not project:
                return jsonify({"error": "Project not found"}), 404

            # Prepare data for the form
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

            # Render form with pre-filled data
            return render_template(
                "edit_project.html",
                project=project_data,
                scrum_masters=scrum_masters,
                user_name=session['username'],
                user_role=session['role'],
                user_id=session['uid']
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Handle POST request (optional, for saving updates)
    elif request.method == "POST":
        try:
            # Fetch project
            project = ProjectDetails.query.get_or_404(project_id)

            # Validations for project-level fields
            project_name = request.form.get("project_name", "").strip()
            if not project_name:
                flash("Project Name is required.", "error")
                return redirect(request.referrer)

            project_description = request.form.get("project_description", "").strip()
            if not project_description:
                flash("Project Description is required.", "error")
                return redirect(request.referrer)

            try:
                start_date = datetime.strptime(
                    request.form["start_date"], "%Y-%m-%d"
                ).date()
                end_date = datetime.strptime(
                    request.form["end_date"], "%Y-%m-%d"
                ).date()
                revised_end_date = datetime.strptime(
                    request.form["revised_end_date"], "%Y-%m-%d"
                ).date()

                if end_date < start_date:
                    flash("End Date cannot be earlier than Start Date.", "error")
                    return redirect(request.referrer)
                if revised_end_date < start_date:
                    flash(
                        "Revised End Date cannot be earlier than Start Date.", "error"
                    )
                    return redirect(request.referrer)
                status=request.form.get('status')
            except ValueError:
                flash("Invalid date format. Use YYYY-MM-DD.", "error")
                return redirect(request.referrer)

            # Update project-level details
            project.ProjectName = project_name
            project.ProjectDescription = project_description
            project.StartDate = start_date
            project.EndDate = end_date
            project.RevisedEndDate = revised_end_date
            project.Status=status
            db.session.commit()

            # Validate and update sprints
            for index, sprint in enumerate(project.sprints):
                sprint_no = request.form.get(f"sprintNo_{index+1}")
                if not sprint_no.isdigit():
                    flash(f"Sprint No for Sprint {index+1} must be a number.", "error")
                    return redirect(request.referrer)

                scrum_master_id = request.form.get(f"scrum_master_id_{index+1}")
                if not scrum_master_id:
                    flash(f"Scrum Master is required for Sprint {index+1}.", "error")
                    return redirect(request.referrer)

                try:
                    sprint_start_date = datetime.strptime(
                        request.form[f"sprint_start_date_{index+1}"], "%Y-%m-%d"
                    ).date()
                    sprint_end_date = datetime.strptime(
                        request.form[f"sprint_end_date_{index+1}"], "%Y-%m-%d"
                    ).date()

                    if sprint_end_date < sprint_start_date:
                        flash(
                            f"End Date cannot be earlier than Start Date for Sprint {index+1}.",
                            "error",
                        )
                        return redirect(request.referrer)
                except ValueError:
                    flash(
                        f"Invalid date format for Sprint {index+1}. Use YYYY-MM-DD.",
                        "error",
                    )
                    return redirect(request.referrer)

                velocity = request.form.get(f"sprint_velocity_{index+1}")
                if not velocity.isdigit() or int(velocity) <= 0:
                    flash(
                        f"Velocity for Sprint {index+1} must be a positive number.",
                        "error",
                    )
                    return redirect(request.referrer)

                # Update sprint details
                sprint.SprintNo = int(sprint_no)
                sprint.ScrumMasterID = int(scrum_master_id)
                sprint.StartDate = sprint_start_date
                sprint.EndDate = sprint_end_date
                sprint.Velocity = int(velocity)
                db.session.commit()

                # Validate and update user stories
                
                # Validate and update user stories
                print(sprint.user_stories)
                for user_story_index, user_story in enumerate(sprint.user_stories):
                    print(f"story_desc_{user_story_index+1}_{user_story_index}", "")
                    user_story_description = request.form.get(
                        f"story_desc_{user_story_index+1}_{user_story_index}", ""
                    ).strip()
                    if not user_story_description:
                        flash(
                            f"Description is required for User Story {user_story_index+1} in Sprint {index+1}.",
                            "error",
                        )
                        return redirect(request.referrer)

                    planned_sprint = request.form.get(
                        f"planned_sprint_{user_story_index+1}_{user_story_index}"
                    )
                    actual_sprint = request.form.get(
                        f"actual_sprint_{user_story_index+1}_{user_story_index}"
                    )

                    if not planned_sprint.isdigit() or not actual_sprint.isdigit():
                        flash(
                            f"Planned and Actual Sprint for User Story {user_story_index+1} in Sprint {index+1} must be numbers.",
                            "error",
                        )
                        return redirect(request.referrer)

                    story_point = request.form.get(
                        f"story_points_{user_story_index+1}_{user_story_index}"
                    )
                    if not story_point.isdigit() or int(story_point) <= 0:
                        flash(
                            f"Story Point for User Story {user_story_index+1} in Sprint {index+1} must be a positive number.",
                            "error",
                        )
                        return redirect(request.referrer)

                    moscow = request.form.get(
                        f"moscow_{user_story_index+1}_{user_story_index}", ""
                    ).strip()
                    if moscow not in [
                        "Must Have",
                        "Should Have",
                        "Could Have",
                        "Won't Have",
                    ]:
                        flash(
                            f"Invalid MOSCOW value for User Story {user_story_index+1} in Sprint {index+1}.",
                            "error",
                        )
                        return redirect(request.referrer)

                    assignee = request.form.get(
                        f"assignee_{user_story_index+1}_{user_story_index}", ""
                    ).strip()
                    if not assignee:
                        flash(
                            f"Assignee is required for User Story {user_story_index+1} in Sprint {index+1}.",
                            "error",
                        )
                        return redirect(request.referrer)

                    status = request.form.get(
                        f"status_{user_story_index+1}_{user_story_index}", ""
                    ).strip()
                    if status not in ["Not Started", "In Progress", "Completed"]:
                        flash(
                            f"Invalid status for User Story {user_story_index+1} in Sprint {index+1}.",
                            "error",
                        )
                        return redirect(request.referrer)

                    # Update user story
                    user_story.Description = user_story_description
                    user_story.PlannedSprint = int(planned_sprint)
                    user_story.ActualSprint = int(actual_sprint)
                    user_story.StoryPoint = int(story_point)
                    user_story.MOSCOW = moscow
                    user_story.Assignee = assignee
                    user_story.Status = status
                    db.session.commit()

            flash("Project successfully updated!", "success")
            return redirect(f"/projects/{session['role']}/{session['uid']}")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")
            print(f"An error occurred: {str(e)}", "error")
            return redirect("/error")

    return render_template(
        "edit_project.html", project=project, scrum_masters=scrum_masters
    )


##### TEAM 3 ROUTES....

@app.route('/viewproject/<int:project_id>', methods=['GET'])
def viewproject(project_id):
    # Fetch project details using the passed project_id
    project = ProjectDetails.query.filter_by(ProjectId=project_id).first()  # Fetch project details
    if not project:
        # If the project is not found, handle the error (optional)
        return "Project not found", 404

    # Fetch user stories related to the specific project
    userstories_data = UserStories.query.filter_by(ProjectId=project_id).all()

    # Prepare the user stories data for the template
    userstories = [
        {
            "us_id": user_story.UserStoryID,
            "description": user_story.Description,
            "status": user_story.Status,
            "assignee": user_story.Assignee,
            "sprint": f"Sprint {user_story.SprintId}"  # Assuming SprintId is used for sprint number
        }
        for user_story in userstories_data
    ]

    # Fetch sprint calendar data related to the specific project
    sprints_data = SprintCalendar.query.filter_by(ProjectId=project_id).all()

    # Prepare the sprint calendar data for the template
    sprintcalendar= [
        {
            "sprint_no": sprint.SprintId,
            "start_date": sprint.StartDate.strftime('%b %d, %Y'),
            "end_date": sprint.EndDate.strftime('%b %d, %Y'),
            "velocity": sprint.Velocity
        }
        for sprint in sprints_data
    ]

    # Pass the project, user stories, and sprints to the template

    #print(sprints)
    return render_template('view.html', userstories=userstories, project=project, sprints=sprintcalendar,
                           user_name=session['username'],
                        )


@app.route('/api/chart-data')
def chart_data():
    try:
        sprints = SprintCalendar.query.all()
        projects = ProjectDetails.query.all()
        user_stories = UserStories.query.all()
        scrum_masters = ScrumMasters.query.all()
        tasks = Tasks.query.all()

        task_status = [{
            "total": len(tasks),
            "completed": (sum(1 for t in tasks if t.TaskStatus == "Completed")),
            "in_progress": sum(1 for t in tasks if t.TaskStatus == "In Progress"),
            "pending": sum(1 for t in tasks if t.TaskStatus == "Not Started")
        }]

        # Prepare data for charts
        sprint_data = [{
            "sprintNo": sprint.SprintNo,
            "velocity": sprint.Velocity,
            "estimatedEffort": sprint.Velocity,
            "actualEffort": sprint.Velocity * 0.85
        } for sprint in sprints]

        sprint_progress = [{
            "sprintNo": sprint.SprintNo,
            "progress": (sum(1 for us in user_stories
                           if us.SprintId == sprint.SprintId and us.Status == "Completed") /
                         len([us for us in user_stories if us.SprintId ==
                             sprint.SprintId]) * 100
                         if len([us for us in user_stories if us.SprintId == sprint.SprintId]) > 0
                         else 0)
        } for sprint in sprints]

  # Updated team_performance logic based on the new requirements
        team_performance = [{
            "team": f"Team {i + 1}",
            "completedTasks": db.session.query(Tasks)
            .filter(Tasks.AssignedUserID == Users.UserID,  # Join Tasks with Users
                    # Match Users.Name with Assignee
                    Users.Name == assignee[0],
                    Tasks.TaskStatus == 'Completed') \
            .count(),
            "completedStories": db.session.query(UserStories)
            .filter(UserStories.Assignee == assignee[0],  # Match Assignee
                    UserStories.Status == 'Completed') \
            .count(),
            "averagePerformance": (
                db.session.query(Tasks)
                .filter(Tasks.AssignedUserID == Users.UserID,
                        Users.Name == assignee[0],
                        Tasks.TaskStatus == 'Completed')
                .count() +
                db.session.query(UserStories)
                .filter(UserStories.Assignee == assignee[0],
                        UserStories.Status == 'Completed')
                .count()
            ) / 2
        } for i, assignee in enumerate(db.session.query(UserStories.Assignee).distinct().all())]

        # Keep the existing return format
        return jsonify({
            "sprintData": sprint_data,
            "sprintProgress": sprint_progress,
            "teamPerformance": team_performance,
            "taskStatus": task_status
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/summary')
def summary():
    try:
        # Fetch data for summary
        projects = ProjectDetails.query.all()
        sprints = SprintCalendar.query.all()
        user_stories = UserStories.query.all()
        tasks = Tasks.query.all()

        # Aggregate project data
        project_summary = {
            "total_projects": len(projects),
            "completed_projects": sum(1 for p in projects if p.Status == "Completed"),
            "active_projects": sum(1 for p in projects if p.Status == "Active"),
            "pending_projects": sum(1 for p in projects if p.Status == "Not Started")
        }

        # Aggregate sprint data
        sprint_summary = {
            "total_sprints": len(sprints),
            "average_velocity": sum(s.Velocity for s in sprints) / len(sprints) if sprints else 0,
            "current_sprint": max(s.SprintNo for s in sprints) if sprints else None
        }

        # Aggregate user story data
        user_story_summary = {
            "total_user_stories": len(user_stories),
            "completed_stories": sum(1 for u in user_stories if u.Status == "Completed"),
            "in_progress_stories": sum(1 for u in user_stories if u.Status == "In Progress"),
            "pending_stories": sum(1 for u in user_stories if u.Status == "Not Started")
        }

        # Aggregate task data
        task_summary = {
            "total_tasks": len(tasks),
            "completed_tasks": sum(1 for t in tasks if t.TaskStatus == "Completed"),
            "in_progress_tasks": sum(1 for t in tasks if t.TaskStatus == "In Progress"),
            "pending_tasks": sum(1 for t in tasks if t.TaskStatus == "Not Started")
        }

        # Combine all summaries
        summary_data = {
            "projects": project_summary,
            "sprints": sprint_summary,
            "user_stories": user_story_summary,
            "tasks": task_summary
        }

        return render_template("summary.html",user_name=session['username'] ,summary_data=summary_data)

    except Exception as e:
        return f"An error occurred while fetching the summary: {e}", 500
    

@app.route('/export-pdf')
def export_pdf():
    pdf_data = generate_pdf()
    return send_file(
        BytesIO(pdf_data),
        as_attachment=True,
        download_name=f'agile_dashboard_report_{datetime.now().strftime("%Y%m%d")}.pdf',
        mimetype='application/pdf'
    )

@app.route('/generate-pdf')
def generate_pdf():
    """
    Generate a detailed Agile Dashboard report in PDF format.

    The report includes:
    - A cover page with title and generation date.
    - Comprehensive explanations about the Agile Dashboard.
    - Detailed summaries of projects, sprints, user stories, and tasks.
    - In-depth descriptions of visual analysis charts (Burn-Down, Burn-Up, etc.).
    - A concluding section.
    Returns:
        A downloadable PDF file.
    """
    try:
        # Fetch data
        projects = ProjectDetails.query.all()
        sprints = SprintCalendar.query.all()
        user_stories = UserStories.query.all()
        tasks = Tasks.query.all()

        # Summarize data
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

        # Initialize PDF
        buffer = BytesIO()
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Cover Page
        pdf.add_page()
        pdf.set_fill_color(200, 200, 200)
        pdf.rect(0, 0, 210, 297, 'F')
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', 'B', 30)
        pdf.cell(0, 120, '', ln=True)  # Spacer
        pdf.cell(0, 20, 'Agile Project Management Dashboard', ln=True, align='C')
        pdf.set_font('Arial', 'I', 16)
        pdf.cell(0, 20, 'Comprehensive Agile Report', ln=True, align='C')
        pdf.cell(0, 20, f"Generated on: {datetime.now().strftime('%B %d, %Y')}", ln=True, align='C')

        # Introduction Page
        pdf.add_page()
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 15, 'Introduction to Agile Dashboard', ln=True)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, """
        The Agile Project Management Dashboard provides an integrated view of all projects, sprints, user stories, and tasks managed by the team. 
        It serves as a centralized platform to monitor progress, assess sprint performance, track story completion, and analyze task execution. 
        This report provides an in-depth summary and analysis of the various components of Agile project management.
        """)

        # Project Overview
        pdf.add_page()
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 15, 'Project Overview', ln=True)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, f"""
        The Agile Dashboard currently tracks a total of {project_summary['total']} projects. These are categorized into:
        - Completed Projects: {project_summary['completed']} ({(project_summary['completed'] / project_summary['total']) * 100:.1f}% of total).
        - Active Projects: {project_summary['active']} (currently in development).
        - Pending Projects: {project_summary['pending']} (in planning phase).

        This distribution highlights the team's focus on delivering high-priority initiatives while actively progressing in other areas.
        """)

        # Sprint Analysis
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 15, 'Sprint Analysis', ln=True)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, f"""
        The dashboard encompasses {sprint_summary['total']} sprints executed to date. Key metrics include:
        - Average Velocity: {sprint_summary['velocity']:.1f} story points per sprint.
        - Current Sprint: #{sprint_summary['current']}.

        The consistent velocity trend indicates efficient planning and execution cycles. Iterative progress ensures adaptive responses to evolving requirements.
        """)

        # User Story Analysis
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 15, 'User Stories Analysis', ln=True)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, f"""
        The total number of user stories in the backlog is {story_summary['total']}, categorized as follows:
        - Completed: {story_summary['completed']} ({(story_summary['completed'] / story_summary['total']) * 100:.1f}% of total).
        - In Progress: {story_summary['in_progress']}.
        - Pending: {story_summary['pending']}.

        These metrics underline the team's commitment to backlog refinement and value delivery.
        """)

        # Task Execution Analysis
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 15, 'Task Execution Analysis', ln=True)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, f"""
        A total of {task_summary['total']} tasks are being tracked, with:
        - {task_summary['completed']} tasks successfully completed.
        - {task_summary['in_progress']} tasks in progress.
        - {task_summary['pending']} tasks yet to be started.

        Task execution reflects the team's operational efficiency and alignment with sprint goals.
        """)

        # Visual Analysis
        pdf.add_page()
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 15, 'Visual Analysis of Agile Metrics', ln=True)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, """
        - Burn-Down Chart: Tracks the remaining effort throughout the sprint lifecycle, helping teams visualize if they are on track.
        - Burn-Up Chart: Illustrates cumulative work completed, ensuring the team meets projected targets.
        - Velocity Chart: Highlights story points achieved per sprint, reflecting team consistency and adaptability.
        - Sprint Progress Chart: Provides a percentage view of sprint completion for effective tracking.
        """)

        # Conclusion
        pdf.add_page()
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 15, 'Conclusion', ln=True)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, """
        The Agile Project Management Dashboard ensures transparency and efficiency in tracking progress and planning future sprints. 
        This report serves as a holistic view of the team's achievements, identifying key strengths and areas for improvement.
        """)

        # Save and Return PDF
        pdf_output = pdf.output(dest='S').encode('latin1')
        buffer.write(pdf_output)
        buffer.seek(0)

        # Save and Return PDF
        pdf_output = pdf.output(dest='S').encode('latin1')
        return pdf_output

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/submit', methods=['POST'])
def submit_project_data():
    try:
        data = request.json
        print(data)

        # Convert date strings to Python datetime.date objects
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        revised_end_date = (
            datetime.strptime(data['revised_end_date'], '%Y-%m-%d').date()
            if data.get('revised_end_date')
            else None
        )
        product_owner = ProductOwner.query.get(data['product_owner_id'])
        # Add Project
        new_project = ProjectDetails(
            ProductOwnerId = data['product_owner_id'],
            ProjectName = data['project_name'],
            ProjectDescription = data['project_description'],
            StartDate = start_date,
            EndDate = end_date,
            RevisedEndDate = revised_end_date,
            Status = data['status']
        )
        db.session.add(new_project)
        db.session.commit()
        print("1st successfull")
        last_project = ProjectDetails.query.order_by(ProjectDetails.ProjectId.desc()).first()
        last_project_id = last_project.ProjectId if last_project else None

        selected_user_ids = data.get('selected_user_ids', '').split(',')
        if not selected_user_ids:
            raise Exception("At least one user must be selected.")
        
        user_emails = []

        for user_id in selected_user_ids:
            if not user_id.isdigit():
                flash(f"Invalid User ID: {user_id}.", "error")
                return redirect(request.referrer)
            user = Users.query.get(int(user_id))
            if not user:
                flash(f"User with ID {user_id} not found.", "error")
                return redirect(request.referrer)
            user_emails.append(user.Email)
            new_project_user = ProjectUsers(
                UserID=user.UserID,
                ProjectId=new_project.ProjectId
            )
            db.session.add(new_project_user)

        # Send emails to product owner and team members
        sm.send_proj_assign_info(
            [product_owner.Email] + user_emails,
            data['project_name'],
            data['project_description'],
            ["Product Owner"] + ["Team Member"] * len(user_emails)
        )
        
        #sprint_no
        i = 1
        # Add Sprints and User Stories
        for sprint in data['sprints']:
            sprint_start_date = datetime.strptime(sprint['start_date'], '%Y-%m-%d').date()
            sprint_end_date = datetime.strptime(sprint['end_date'], '%Y-%m-%d').date()



            new_sprint = SprintCalendar(
                ProjectId = last_project_id,
                SprintNo = i,
                ScrumMasterID = sprint['scrum_master_id'],
                StartDate = sprint_start_date,
                EndDate = sprint_end_date,
                Velocity = sprint['velocity']

            )
            i+=1
            db.session.add(new_sprint)
            db.session.commit()
            print("2nd successfull")

            for story in sprint['user_stories']:
                last_sprint = SprintCalendar.query.order_by(SprintCalendar.SprintId.desc()).first()
                last_sprint_id = last_sprint.SprintId if last_sprint else None
                new_story = UserStories(
                        ProjectId = last_project_id,
                        SprintId = last_sprint_id,
                        PlannedSprint = story['planned_sprint'],
                        ActualSprint = story['actual_sprint'],
                        Description = story['description'],
                        StoryPoint = story['story_points'],
                        MOSCOW = story['moscow'],
                        Assignee = story['assignee'],
                        Status = story['status']
                )
                db.session.add(new_story)
                db.session.commit()
                print("3rd successfull")

        return jsonify({"message": "Project, sprints, and user stories added successfully." , "redirect" : url_for('projects', role=session['role'], userid=session['uid'])}),201

    except Exception as e:
        db.session.rollback()
        print("Full error traceback:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400


#### TEAM 4 CODE ....


def schedule_reports():
    while True:
        schedule.run_pending()
        time.sleep(1)

def generate_scheduled_report(report_type):
    try:
        with app.app_context():
            # Create reports directory if it doesn't exist
            os.makedirs('reports', exist_ok=True)

            # Generate the PDF
            pdf_data = generate_pdf()

            # Determine the file name and path
            report_date = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f'automated_report_{report_type}_{report_date}.pdf'
            file_path = os.path.join('reports', file_name)

            # Check for existing report to prevent duplicates
            existing_report = Reports.query.filter_by(
                Filename=file_name).first()
            if existing_report:
                print(
                    f"Report {file_name} already exists. Skipping generation.")
                return

            # Save PDF to file
            with open(file_path, 'wb') as f:
                f.write(pdf_data)

            # Store report record in database
            new_report = Reports(
                Filename=file_name,
                Filepath=file_path,
                Frequency=FrequencyEnum[report_type.upper()],
                ProjectId=1  # You may want to pass this as a parameter
            )
            db.session.add(new_report)
            db.session.commit()

            print(f"{report_type.capitalize()} report generated and stored: {file_path}")
            sm.send_email_with_report(report_type.capitalize(), file_path)

    except Exception as e:
        print(f"An error occurred while generating the scheduled report: {e}")


# Route to manually trigger report generation (for Vercel/production)
@app.route('/generate-report/<report_type>')
def manual_report_generation(report_type):
    """Manual report generation endpoint for production environments"""
    try:
        generate_scheduled_report(report_type)
        return jsonify({"message": f"{report_type.capitalize()} report generated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    # Setup scheduled reports for local development
    setup_scheduled_reports()
    app.run(debug=True)

# For production (Vercel), the app object will be imported by wsgi.py
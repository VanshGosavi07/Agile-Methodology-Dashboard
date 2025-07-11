from database import db 
from flask_login import UserMixin
from datetime import datetime
from enum import Enum
# ProductOwner Table
class ProductOwner(db.Model):
    __tablename__ = 'ProductOwner'
    ProductOwnerId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(255), nullable=False)
    Email = db.Column(db.String(255), unique=True, nullable=False)
    RoleName = db.Column(db.String(255), nullable=False)

    # Relationships
    projects = db.relationship('ProjectDetails', backref='product_owner', lazy=True)

    def __repr__(self):
        return f"<ProductOwner {self.Name}>"

# ProjectDetails Table
class ProjectDetails(db.Model):
    __tablename__ = 'ProjectDetails'
    ProjectId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ProductOwnerId = db.Column(db.Integer, db.ForeignKey('ProductOwner.ProductOwnerId'), nullable=False)
    ProjectName = db.Column(db.String(255), nullable=False)
    ProjectDescription = db.Column(db.Text)
    StartDate = db.Column(db.Date, nullable=False)
    EndDate = db.Column(db.Date, nullable=False)
    RevisedEndDate = db.Column(db.Date)
    Status = db.Column(db.String(100), default="Not Started")

    # Relationships
    sprints = db.relationship('SprintCalendar', backref='project', lazy=True)
    user_stories = db.relationship('UserStories', backref='project', lazy=True)

    def __repr__(self):
        return f"<ProjectDetails {self.ProjectName}>"

# SprintCalendar Table
class SprintCalendar(db.Model):
    __tablename__ = 'SprintCalendar'
    SprintId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ProjectId = db.Column(db.Integer, db.ForeignKey('ProjectDetails.ProjectId'), nullable=False)
    ScrumMasterID = db.Column(db.Integer, db.ForeignKey('ScrumMasters.ScrumMasterID'), nullable=True)
    SprintNo = db.Column(db.Integer, nullable=True)
    StartDate = db.Column(db.Date, nullable=False)
    EndDate = db.Column(db.Date, nullable=False)
    Velocity = db.Column(db.Integer, default=0)

    # Relationships
    scrum_master = db.relationship('ScrumMasters', backref='sprints')
    user_stories = db.relationship('UserStories', backref='sprint', lazy=True)

    def __repr__(self):
        return f"<SprintCalendar Sprint {self.SprintNo}>"

# ScrumMasters Table
class ScrumMasters(db.Model):
    __tablename__ = 'ScrumMasters'
    ScrumMasterID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Email = db.Column(db.String(255), nullable=False, unique=True)
    Name = db.Column(db.String(255), nullable=False)
    ContactNumber = db.Column(db.String(15))

    def __repr__(self):
        return f"<ScrumMasters {self.Name}>"

# Users Table
class Users(db.Model, UserMixin):
    __tablename__ = 'Users'
    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserName = db.Column(db.String(255), unique=True, nullable=False)
    Password = db.Column(db.String(255), nullable=False)
    Email = db.Column(db.String(255), unique=True, nullable=False)
    Role = db.Column(db.String(100), nullable=False)
    PhoneNumber = db.Column(db.String(15))
    Name = db.Column(db.String(255), nullable=False)
    Approved = db.Column(db.Boolean, default=False)
    DOB = db.Column(db.DateTime,nullable=True)
    login_time = db.Column(db.DateTime, nullable=True)
    logout_time = db.Column(db.DateTime, nullable=True)
    profile_picture = db.Column(db.String(100))  # Store the file path of the profile picture
    def get_id(self):
        return str(self.UserID)

    # Relationships
    tasks = db.relationship('Tasks', backref='assigned_user', lazy=True)
    roles = db.relationship('UserRoles', backref='user', lazy=True)

    def __repr__(self):
        return f"<Users {self.UserName}>"
        # Override the get_id method



# Tasks Table
class Tasks(db.Model):
    __tablename__ = 'Tasks'
    TaskId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserStoryID = db.Column(db.Integer, db.ForeignKey('UserStories.UserStoryID'), nullable=False)
    TaskName = db.Column(db.String(255), nullable=False)
    AssignedUserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    TaskStatus = db.Column(db.String(100), default="Not Started")

    # Relationships
    user_story = db.relationship('UserStories', backref='tasks')

    def __repr__(self):
        return f"<Tasks {self.TaskName}>"

# UserRoles Table
class UserRoles(db.Model):
    __tablename__ = 'UserRoles'
    RoleID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    RoleName = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<UserRoles {self.RoleName}>"

# UserStories Table
class UserStories(db.Model):
    __tablename__ = 'UserStories'
    UserStoryID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ProjectId = db.Column(db.Integer, db.ForeignKey('ProjectDetails.ProjectId'), nullable=False)
    SprintId = db.Column(db.Integer, db.ForeignKey('SprintCalendar.SprintId'), nullable=True)
    PlannedSprint = db.Column(db.Integer, nullable=False)
    ActualSprint = db.Column(db.Integer, nullable=False)
    Description = db.Column(db.Text, nullable=False)
    StoryPoint = db.Column(db.Integer, nullable=False)
    MOSCOW = db.Column(db.String(50), nullable=False)
    Assignee = db.Column(db.String(255))
    Status = db.Column(db.String(100), default="Not Started")

    def __repr__(self):
        return f"<UserStories {self.Description[:20]}>"

class ProjectUsers(db.Model):
    __tablename__ = 'ProjectUsers'

    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), primary_key=True, nullable=False)
    ProjectId = db.Column(db.Integer, db.ForeignKey('ProjectDetails.ProjectId'), primary_key=True, nullable=False)

    # Relationships (optional, for convenience in accessing related objects)
    user = db.relationship('Users', backref='project_associations')
    project = db.relationship('ProjectDetails', backref='user_associations')

    def __repr__(self):
        return f"<ProjectUsers(user_id={self.user_id}, project_id={self.project_id})>"
    
class FrequencyEnum(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class Reports(db.Model):
    __tablename__ = 'Reports'
    ReportId = db.Column(db.Integer, primary_key=True)
    Filename = db.Column(db.String(255), nullable=False)
    Filepath = db.Column(db.String(255), nullable=False)
    GeneratedOn = db.Column(db.DateTime, default=datetime.utcnow)
    Frequency = db.Column(db.Enum(FrequencyEnum), nullable=False)
    ProjectId = db.Column(db.Integer, db.ForeignKey(
        'ProjectDetails.ProjectId'), nullable=False)

    project = db.relationship('ProjectDetails', backref='reports')
from database import db
from flask_login import UserMixin
from datetime import datetime
from enum import Enum

# ==================== Organization Model ====================
# Represents a company/organization in the multi-tenant system
# NOTE: Subscription limits REMOVED - all organizations have UNLIMITED users and projects

class Organization(db.Model):
    """
    Organization model for multi-tenant support.
    Each organization has complete data isolation.
    
    IMPORTANT: MaxUsers and MaxProjects fields have been REMOVED
    All organizations now have unlimited access to users and projects.
    """
    __tablename__ = 'Organization'
    
    # Primary key
    OrgID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Organization details
    OrgName = db.Column(db.String(255), nullable=False, unique=True)
    OrgEmail = db.Column(db.String(255), nullable=True)
    ContactPerson = db.Column(db.String(255), nullable=True)
    PhoneNumber = db.Column(db.String(15), nullable=True)
    Domain = db.Column(db.String(255), unique=True, nullable=True)  # e.g., company.com
    Approved = db.Column(db.Boolean, default=False)  # Organization needs approval
    IsActive = db.Column(db.Boolean, default=True)
    CreatedDate = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships - one organization has many users, projects, etc.
    users = db.relationship('Users', backref='organization', lazy=True)
    projects = db.relationship('ProjectDetails', backref='organization', lazy=True)
    product_owners = db.relationship('ProductOwner', backref='organization', lazy=True)
    scrum_masters = db.relationship('ScrumMasters', backref='organization', lazy=True)

    def __repr__(self):
        return f"<Organization {self.OrgName}>"

class ProductOwner(db.Model):
    __tablename__ = 'ProductOwner'
    ProductOwnerId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrgID = db.Column(db.Integer, db.ForeignKey('Organization.OrgID'), nullable=False, index=True)
    Name = db.Column(db.String(255), nullable=False)
    Email = db.Column(db.String(255), nullable=False, index=True)
    RoleName = db.Column(db.String(255), nullable=False)

    projects = db.relationship('ProjectDetails', backref='product_owner', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('Email', 'OrgID', name='unique_po_email_per_org'),
        db.Index('idx_po_org_email', 'OrgID', 'Email'),
    )

    def __repr__(self):
        return f"<ProductOwner {self.Name}>"

class ProjectDetails(db.Model):
    __tablename__ = 'ProjectDetails'
    ProjectId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrgID = db.Column(db.Integer, db.ForeignKey('Organization.OrgID'), nullable=False, index=True)
    ProductOwnerId = db.Column(db.Integer, db.ForeignKey('ProductOwner.ProductOwnerId'), nullable=False)
    ProjectName = db.Column(db.String(255), nullable=False)
    ProjectDescription = db.Column(db.Text)
    StartDate = db.Column(db.Date, nullable=False)
    EndDate = db.Column(db.Date, nullable=False)
    RevisedEndDate = db.Column(db.Date)
    Status = db.Column(db.String(100), default="Not Started")
    CreatedDate = db.Column(db.DateTime, default=datetime.utcnow)
    UpdatedDate = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sprints = db.relationship('SprintCalendar', backref='project', lazy=True, cascade='all, delete-orphan')
    user_stories = db.relationship('UserStories', backref='project', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_project_org_status', 'OrgID', 'Status'),
        db.Index('idx_project_org_dates', 'OrgID', 'StartDate', 'EndDate'),
    )

    def __repr__(self):
        return f"<ProjectDetails {self.ProjectName}>"

class SprintCalendar(db.Model):
    __tablename__ = 'SprintCalendar'
    SprintId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ProjectId = db.Column(db.Integer, db.ForeignKey('ProjectDetails.ProjectId'), nullable=False)
    ScrumMasterID = db.Column(db.Integer, db.ForeignKey('ScrumMasters.ScrumMasterID'), nullable=True)
    SprintNo = db.Column(db.Integer, nullable=True)
    StartDate = db.Column(db.Date, nullable=False)
    EndDate = db.Column(db.Date, nullable=False)
    Velocity = db.Column(db.Integer, default=0)

    scrum_master = db.relationship('ScrumMasters', backref='sprints')
    user_stories = db.relationship('UserStories', backref='sprint', lazy=True)

    def __repr__(self):
        return f"<SprintCalendar Sprint {self.SprintNo}>"

class ScrumMasters(db.Model):
    __tablename__ = 'ScrumMasters'
    ScrumMasterID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrgID = db.Column(db.Integer, db.ForeignKey('Organization.OrgID'), nullable=False, index=True)
    Email = db.Column(db.String(255), nullable=False, index=True)
    Name = db.Column(db.String(255), nullable=False)
    ContactNumber = db.Column(db.String(15))

    __table_args__ = (
        db.UniqueConstraint('Email', 'OrgID', name='unique_sm_email_per_org'),
        db.Index('idx_sm_org', 'OrgID'),
    )

    def __repr__(self):
        return f"<ScrumMasters {self.Name}>"

class Users(db.Model, UserMixin):
    __tablename__ = 'Users'
    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrgID = db.Column(db.Integer, db.ForeignKey('Organization.OrgID'), nullable=False, index=True)
    UserName = db.Column(db.String(255), nullable=False, index=True)
    Password = db.Column(db.String(255), nullable=False)
    Email = db.Column(db.String(255), nullable=False, index=True)
    Role = db.Column(db.String(100), nullable=False)
    PhoneNumber = db.Column(db.String(15))
    Name = db.Column(db.String(255), nullable=False)
    Approved = db.Column(db.Boolean, default=False)
    DOB = db.Column(db.DateTime,nullable=True)
    login_time = db.Column(db.DateTime, nullable=True)
    logout_time = db.Column(db.DateTime, nullable=True)
    profile_picture = db.Column(db.String(500))  # Increased for Cloudinary URLs
    IsActive = db.Column(db.Boolean, default=True)
    CreatedDate = db.Column(db.DateTime, default=datetime.utcnow)

    def get_id(self):
        return str(self.UserID)

    tasks = db.relationship('Tasks', backref='assigned_user', lazy=True)
    roles = db.relationship('UserRoles', backref='user', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('UserName', 'OrgID', name='unique_username_per_org'),
        db.UniqueConstraint('Email', 'OrgID', name='unique_email_per_org'),
        db.Index('idx_user_org_email', 'OrgID', 'Email'),
        db.Index('idx_user_org_role', 'OrgID', 'Role'),
    )

    def __repr__(self):
        return f"<Users {self.UserName}>"



class Tasks(db.Model):
    __tablename__ = 'Tasks'
    TaskId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserStoryID = db.Column(db.Integer, db.ForeignKey('UserStories.UserStoryID'), nullable=False)
    TaskName = db.Column(db.String(255), nullable=False)
    AssignedUserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    TaskStatus = db.Column(db.String(100), default="Not Started")

    user_story = db.relationship('UserStories', backref='tasks')

    def __repr__(self):
        return f"<Tasks {self.TaskName}>"

class UserRoles(db.Model):
    __tablename__ = 'UserRoles'
    RoleID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    RoleName = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<UserRoles {self.RoleName}>"

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
    Filepath = db.Column(db.String(500), nullable=False)  # Increased for Cloudinary URLs
    GeneratedOn = db.Column(db.DateTime, default=datetime.utcnow)
    Frequency = db.Column(db.Enum(FrequencyEnum), nullable=False)
    ProjectId = db.Column(db.Integer, db.ForeignKey(
        'ProjectDetails.ProjectId'), nullable=False)

    project = db.relationship('ProjectDetails', backref='reports')


class AuditLog(db.Model):
    __tablename__ = 'AuditLog'
    LogID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrgID = db.Column(db.Integer, db.ForeignKey('Organization.OrgID'), nullable=False, index=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=True)
    Action = db.Column(db.String(100), nullable=False)
    ResourceType = db.Column(db.String(100), nullable=False)
    ResourceID = db.Column(db.Integer, nullable=True)
    Details = db.Column(db.Text, nullable=True)
    IPAddress = db.Column(db.String(45), nullable=True)
    UserAgent = db.Column(db.String(255), nullable=True)
    Timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('Users', backref='audit_logs')

    __table_args__ = (
        db.Index('idx_audit_org_time', 'OrgID', 'Timestamp'),
        db.Index('idx_audit_org_action', 'OrgID', 'Action'),
    )

    def __repr__(self):
        return f"<AuditLog {self.Action} by User {self.UserID}>"


class Notification(db.Model):
    __tablename__ = 'Notification'
    NotificationID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrgID = db.Column(db.Integer, db.ForeignKey('Organization.OrgID'), nullable=False, index=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    Title = db.Column(db.String(255), nullable=False)
    Message = db.Column(db.Text, nullable=False)
    Type = db.Column(db.String(50), default="info")
    IsRead = db.Column(db.Boolean, default=False)
    CreatedDate = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ReadDate = db.Column(db.DateTime, nullable=True)

    user = db.relationship('Users', backref='notifications')

    __table_args__ = (
        db.Index('idx_notif_user_read', 'UserID', 'IsRead'),
        db.Index('idx_notif_org_created', 'OrgID', 'CreatedDate'),
    )

    def __repr__(self):
        return f"<Notification {self.Title}>"
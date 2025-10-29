from flask import request, jsonify, render_template, redirect, url_for, session, Blueprint,current_app, flash
from datetime import datetime, timedelta, date
import password_utils as pw
import send_mail as sm
import random
from models import Users
from database import db
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import os
import csv
from werkzeug.utils import secure_filename
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
from flask import send_file
from plotly.graph_objects import Figure
import traceback
from cloudinary_storage import upload_profile_image, initialize_cloudinary



CSV_FILE = "user_history.csv"

login_manager = LoginManager()
login_bp = Blueprint('auth', __name__)

# Helper function to get CSV file path (use /tmp in production)
def get_csv_path(filename):
    """Returns writable path for CSV files - /tmp in production, local in dev"""
    if os.environ.get('GAE_ENV', '').startswith('standard'):
        # Google App Engine - use /tmp directory
        tmp_path = os.path.join('/tmp', filename)
        # Initialize CSV if it doesn't exist
        if not os.path.exists(tmp_path):
            with open(tmp_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                if 'user_history' in filename:
                    writer.writerow(["User ID","Username", "Role", "Action", "Timestamp", "IP Address"])
                elif 'failed_login' in filename:
                    writer.writerow(["Username", "Timestamp", "IP Address"])
        return tmp_path
    else:
        # Development - use local directory
        if not os.path.exists(filename):
            with open(filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                if 'user_history' in filename:
                    writer.writerow(["User ID","Username", "Role", "Action", "Timestamp", "IP Address"])
                elif 'failed_login' in filename:
                    writer.writerow(["Username", "Timestamp", "IP Address"])
        return filename



# Removed: os.makedirs('static/uploads', exist_ok=True) - No longer needed with Cloudinary

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@login_manager.user_loader
def load_user(user_id):
    try:
        return Users.query.get(int(user_id))
    except Exception as e:
        print(f"Error loading user: {e}")
        return None


def otp_generator():
    return random.randint(100000, 999999)

# CSV initialization removed - App Engine has read-only filesystem
# CSV files will be managed in Cloudinary storage only

def backup_csv_to_cloudinary(csv_file_path):
    """Backup CSV file to Cloudinary Storage"""
    try:
        from cloudinary_storage import upload_csv_file, initialize_cloudinary
        initialize_cloudinary()
        success, result = upload_csv_file(csv_file_path)
        if success:
            print(f"[INFO] CSV backed up to Cloudinary: {result}")
        else:
            print(f"[WARNING] Failed to backup CSV to Cloudinary: {result}")
    except Exception as e:
        print(f"[ERROR] CSV backup error: {str(e)}")

def log_to_csv(user_id, action):
    user = db.session.execute(db.Select(Users).where(Users.UserID==user_id)).scalar()
    print(user.UserName, user)
    csv_path = get_csv_path(CSV_FILE)
    with open(csv_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ip_address = request.remote_addr or "Unknown"
        writer.writerow([user_id, user.UserName, user.Role, action, timestamp, ip_address])
    
    # Backup to Cloudinary after logging
    backup_csv_to_cloudinary(csv_path)


def get_history_from_csv(user_id):
    history = []
    csv_path = get_csv_path(CSV_FILE)
    with open(csv_path, mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            if int(row['User ID']) == user_id:
                history.append({
                    'id': row['User ID'],
                    'username': row['Username'],
                    'role': row['Role'],
                    'action': row['Action'],
                    'timestamp': row['Timestamp'],
                    'ip_address': row['IP Address']
                })
    return history


@login_bp.route('/history/<int:user_id>', methods=['POST'])
def history(user_id):
    history = get_history_from_csv(user_id)
    print(history)
    return render_template('history.html', history=history)

FAILED_LOGIN_CSV_FILE = "failed_login_history.csv"

# CSV initialization removed - App Engine has read-only filesystem
# CSV files will be managed in Cloudinary storage only

def log_failed_login(username):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip_address = request.remote_addr or "Unknown"
    csv_path = get_csv_path(FAILED_LOGIN_CSV_FILE)
    with open(csv_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([username, timestamp, ip_address])
    
    # Backup to Cloudinary after logging
    backup_csv_to_cloudinary(csv_path)




@login_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user = Users.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    sm.user_deleted(user.Email, user)
    return redirect(url_for('auth.admin_dashboard'))


@login_bp.route('/update_approval/<int:user_id>', methods=['POST'])
@login_required
def update_approval(user_id):
    user = Users.query.get_or_404(user_id)
    approved = 'approved' in request.form
    user.Approved = approved
    db.session.commit()
    sm.user_approved(user.Email, user)
    return redirect(url_for('auth.admin_dashboard'))


@login_bp.route('/register_organization', methods=['GET', 'POST'])
def register_organization():
    """
    Handle organization registration.
    Organizations are auto-approved upon creation.
    The person who creates the organization should register as an admin.
    Users who join existing organizations need approval from that org's admin.
    """
    if request.method == 'POST':
        try:
            from models import Organization
            
            # Get form data
            org_name = request.form.get('org_name', '').strip()
            org_email = request.form.get('org_email', '').strip()
            contact_person = request.form.get('contact_person', '').strip()
            phone_number = request.form.get('phone_number', '').strip()
            domain = request.form.get('domain', '').strip()
            
            # Validate organization name
            if not org_name:
                flash("Organization name is required.", "error")
                return redirect(url_for('auth.register_organization'))
            
            if len(org_name) < 3:
                flash("Organization name must be at least 3 characters long.", "error")
                return redirect(url_for('auth.register_organization'))
            
            # Check if organization already exists
            existing_org = Organization.query.filter_by(OrgName=org_name).first()
            if existing_org:
                flash("Organization name already exists. Please choose another.", "error")
                return redirect(url_for('auth.register_organization'))
            
            # Validate email
            if org_email:
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, org_email):
                    flash("Invalid email format.", "error")
                    return redirect(url_for('auth.register_organization'))
            
            # Validate domain if provided
            if domain:
                existing_domain = Organization.query.filter_by(Domain=domain).first()
                if existing_domain:
                    flash("Domain already registered to another organization.", "error")
                    return redirect(url_for('auth.register_organization'))
            
            # Create new organization (auto-approved)
            new_org = Organization(
                OrgName=org_name,
                OrgEmail=org_email,
                ContactPerson=contact_person,
                PhoneNumber=phone_number,
                Domain=domain,
                Approved=True,  # Auto-approved - the creator will be the admin
                IsActive=True
            )
            
            db.session.add(new_org)
            db.session.commit()
            
            print(f"[SUCCESS] New organization created: {org_name} (ID: {new_org.OrgID}) - Auto-Approved")
            
            flash(f'Organization "{org_name}" registered successfully! You can now register as admin for this organization.', 'success')
            return redirect(url_for('auth.add_user'))
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Organization registration failed: {str(e)}")
            print(traceback.format_exc())
            flash(f"Registration failed: {str(e)}", "error")
            return redirect(url_for('auth.register_organization'))
    
    # GET request - display organization registration form
    return render_template('register_organization.html')


@login_bp.route('/', methods=['GET', 'POST'])
@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login with credentials validation, OTP generation, and comprehensive error handling.
    
    GET: Display login form
    POST: Validate credentials, generate OTP, send email
    
    Returns:
        template: Login page on GET or error
        redirect: To OTP verification on success
        
    Validates:
        - Username and password presence
        - User existence in database
        - Password correctness
        - Account approval status
    """
    if request.method == 'POST':
        try:
            # Validate input presence
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            if not username:
                session['error_message'] = "Username is required."
                return redirect(url_for('auth.login'))
            
            if not password:
                session['error_message'] = "Password is required."
                return redirect(url_for('auth.login'))
            
            # Validate username length and format
            if len(username) < 3:
                session['error_message'] = "Username must be at least 3 characters."
                return redirect(url_for('auth.login'))
            
            if len(username) > 100:
                session['error_message'] = "Username is too long."
                return redirect(url_for('auth.login'))
            
            # Query user from database
            user = Users.query.filter_by(UserName=username).first()
            
            # Validate user existence and password
            if user and pw.verify_password(user.Password, password):
                # Check approval status (admins don't need approval)
                if not user.Approved and user.Role != 'admin':
                    session['error_message'] = "Your account is not approved by the admin."
                    log_failed_login(username)
                    return redirect(url_for('auth.login'))
                
                # Clear any previous error messages
                session.pop('error_message', None)
                
                # Generate and send OTP
                try:
                    otp = otp_generator()
                    sm.send_otp_email(user.Email, otp)
                except Exception as email_error:
                    print(f"[ERROR] Failed to send OTP email to {user.Email}: {str(email_error)}")
                    session['error_message'] = "Failed to send OTP. Please try again."
                    return redirect(url_for('auth.login'))
                
                # Store OTP and user info in session
                session['otp'] = otp
                session['otp_expiry'] = (datetime.now() + timedelta(minutes=5)).isoformat()
                session['username'] = user.UserName
                session['role'] = user.Role
                session['uid'] = user.UserID
                
                # Log successful login attempt
                try:
                    log_to_csv(user.UserID, "Login")
                except Exception as log_error:
                    print(f"[WARNING] Failed to log login for user {user.UserID}: {str(log_error)}")
                
                print(f"[INFO] Login successful for user: {username}")
                return redirect(url_for('auth.verify_otp'))
            
            else:
                # Invalid credentials
                log_failed_login(username)
                session['error_message'] = 'Wrong username or password. Please try again.'
                print(f"[WARNING] Failed login attempt for username: {username}")
                return redirect(url_for('auth.login'))
                
        except Exception as e:
            print(f"[ERROR] Login failed: {str(e)}")
            print(traceback.format_exc())
            session['error_message'] = "An error occurred during login. Please try again."
            return redirect(url_for('auth.login'))
    
    # GET request - display login form
    error_message = session.pop('error_message', None)
    return render_template('login.html', error_message=error_message)


@login_bp.route('/add_user', methods=['POST', 'GET'])
@login_bp.route('/signup', methods=['POST', 'GET'])
def add_user():
    """
    Handle user registration with comprehensive input validation and error handling.
    
    GET: Display signup form
    POST: Validate inputs, create user account, send approval notifications
    
    Returns:
        template: Signup page on GET or error
        redirect: To login page on successful registration
        
    Validates:
        - Username uniqueness and format
        - Email format and uniqueness
        - Password strength
        - Date of birth validity
        - Phone number format
        - Profile picture file type
    """
    if request.method == 'POST':
        try:
            # ========== Validate Basic Inputs ==========
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            name = request.form.get('name', '').strip()
            password = request.form.get('password', '').strip()
            dob_str = request.form.get('dob', '').strip()
            role = request.form.get('role', '').strip()
            phone_number = request.form.get('phone_number', '').strip()
            
            # Validate username
            if not username:
                flash("Username is required.", "error")
                return redirect(url_for('auth.add_user'))
            
            if len(username) < 3:
                flash("Username must be at least 3 characters long.", "error")
                return redirect(url_for('auth.add_user'))
            
            if len(username) > 100:
                flash("Username cannot exceed 100 characters.", "error")
                return redirect(url_for('auth.add_user'))
            
            # Check username uniqueness
            existing_user = Users.query.filter_by(UserName=username).first()
            if existing_user:
                flash("Username already exists. Please choose another.", "error")
                return redirect(url_for('auth.add_user'))
            
            # Validate email
            if not email:
                flash("Email is required.", "error")
                return redirect(url_for('auth.add_user'))
            
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                flash("Invalid email format.", "error")
                return redirect(url_for('auth.add_user'))
            
            # Check email uniqueness
            existing_email = Users.query.filter_by(Email=email).first()
            if existing_email:
                flash("Email already registered. Please use another.", "error")
                return redirect(url_for('auth.add_user'))
            
            # Validate name
            if not name:
                flash("Name is required.", "error")
                return redirect(url_for('auth.add_user'))
            
            if len(name) < 2:
                flash("Name must be at least 2 characters long.", "error")
                return redirect(url_for('auth.add_user'))
            
            # Validate password
            if not password:
                flash("Password is required.", "error")
                return redirect(url_for('auth.add_user'))
            
            if len(password) < 8:
                flash("Password must be at least 8 characters long.", "error")
                return redirect(url_for('auth.add_user'))
            
            # Validate date of birth
            if not dob_str:
                flash("Date of birth is required.", "error")
                return redirect(url_for('auth.add_user'))
            
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                
                # Check if DOB is in the future
                if dob > date.today():
                    flash("Date of birth cannot be in the future.", "error")
                    return redirect(url_for('auth.add_user'))
                
                # Check minimum age (e.g., 13 years old)
                age = (date.today() - dob).days / 365.25
                if age < 13:
                    flash("You must be at least 13 years old to register.", "error")
                    return redirect(url_for('auth.add_user'))
                    
            except ValueError:
                flash("Invalid date format. Use YYYY-MM-DD.", "error")
                return redirect(url_for('auth.add_user'))
            
            # Validate role
            valid_roles = ['admin', 'product owner', 'scrum master', 'developer', 'tester']
            if not role or role.lower() not in valid_roles:
                flash(f"Invalid role. Must be one of: {', '.join(valid_roles)}", "error")
                return redirect(url_for('auth.add_user'))
            
            # Validate phone number
            if phone_number:
                phone_pattern = r'^\+?1?\d{9,15}$'
                if not re.match(phone_pattern, phone_number):
                    flash("Invalid phone number format. Use 9-15 digits.", "error")
                    return redirect(url_for('auth.add_user'))
            
            # ========== Hash Password ==========
            hashed_password = pw.hash_password(password)
            
            # Determine approval status (admins auto-approved)
            approved = (role.lower() == "admin")
            
            # ========== Handle Profile Picture Upload ==========
            profile_picture_url = None  # Default - no profile picture
            file = request.files.get('file')
            
            if file and file.filename:
                if allowed_file(file.filename):
                    try:
                        # Initialize Cloudinary
                        initialize_cloudinary()
                        
                        # Upload to Cloudinary Storage
                        success, result = upload_profile_image(file, None)  # user_id is None since user not created yet
                        
                        if success:
                            profile_picture_url = result  # Cloudinary public URL
                            print(f"[INFO] Profile picture uploaded to Cloudinary: {profile_picture_url}")
                            flash("Profile picture uploaded successfully!", "success")
                        else:
                            print(f"[ERROR] Failed to upload profile picture to Cloudinary: {result}")
                            flash("Profile picture upload failed. Proceeding without image.", "warning")
                    except Exception as file_error:
                        print(f"[ERROR] Exception during profile picture upload: {str(file_error)}")
                        flash("Profile picture upload skipped. Proceeding without image.", "info")
                else:
                    flash("Invalid file type. Allowed: jpg, jpeg, png, gif", "error")
                    return redirect(url_for('auth.add_user'))
            
            # ========== Handle Organization Assignment ==========
            from models import Organization
            
            # Check if admin is creating a new organization
            create_new_org = request.form.get('create_new_org', 'false').strip().lower()
            
            if create_new_org == 'true' and role.lower() == 'admin':
                # Admin is creating a new organization
                new_org_name = request.form.get('new_org_name', '').strip()
                new_org_email = request.form.get('new_org_email', '').strip()
                new_org_contact = request.form.get('new_org_contact', '').strip()
                new_org_phone = request.form.get('new_org_phone', '').strip()
                new_org_domain = request.form.get('new_org_domain', '').strip()
                
                # Validate new organization name
                if not new_org_name or len(new_org_name) < 3:
                    flash("Organization name is required and must be at least 3 characters.", "error")
                    return redirect(url_for('auth.add_user'))
                
                # Check if organization already exists
                existing_org = Organization.query.filter_by(OrgName=new_org_name).first()
                if existing_org:
                    flash("Organization name already exists. Please choose another.", "error")
                    return redirect(url_for('auth.add_user'))
                
                # Validate domain uniqueness if provided
                if new_org_domain:
                    existing_domain = Organization.query.filter_by(Domain=new_org_domain).first()
                    if existing_domain:
                        flash("Domain already registered to another organization.", "error")
                        return redirect(url_for('auth.add_user'))
                
                # Create new organization (auto-approved)
                selected_org = Organization(
                    OrgName=new_org_name,
                    OrgEmail=new_org_email if new_org_email else None,
                    ContactPerson=new_org_contact if new_org_contact else None,
                    PhoneNumber=new_org_phone if new_org_phone else None,
                    Domain=new_org_domain if new_org_domain else None,
                    Approved=True,  # Auto-approved
                    IsActive=True
                )
                
                db.session.add(selected_org)
                db.session.flush()  # Get the OrgID without committing yet
                
                print(f"[SUCCESS] New organization created: {new_org_name} (ID: {selected_org.OrgID}) during admin registration")
                
            else:
                # Use existing organization
                org_id = request.form.get('organization', '').strip()
                
                if not org_id:
                    flash("Please select an organization.", "error")
                    return redirect(url_for('auth.add_user'))
                
                try:
                    org_id = int(org_id)
                except ValueError:
                    flash("Invalid organization selected.", "error")
                    return redirect(url_for('auth.add_user'))
                
                # Validate organization exists and is approved
                selected_org = Organization.query.filter_by(OrgID=org_id, Approved=True, IsActive=True).first()
                
                if not selected_org:
                    flash("Selected organization is not available or not approved yet.", "error")
                    return redirect(url_for('auth.add_user'))
            
            # ========== Create New User ==========
            new_user = Users(
                OrgID=selected_org.OrgID,  # Assign selected organization ID
                UserName=username,
                Password=hashed_password.decode('utf-8'),
                Email=email,
                Name=name,
                DOB=dob,
                Role=role,
                PhoneNumber=phone_number,
                Approved=approved,
                profile_picture=profile_picture_url  # Store Cloudinary URL or None
            )
            
            # ========== Save to Database ==========
            db.session.add(new_user)
            db.session.commit()
            print(f"[SUCCESS] New user created: {username} (Role: {role})")
            
            # ========== Add to Role-Specific Tables ==========
            try:
                if role.lower() == 'product owner':
                    from models import ProductOwner
                    product_owner = ProductOwner(
                        OrgID=selected_org.OrgID,
                        Name=name,
                        Email=email,
                        RoleName='product owner'
                    )
                    db.session.add(product_owner)
                    db.session.commit()
                    print(f"[SUCCESS] Added {name} to ProductOwner table")
                
                elif role.lower() == 'scrum master':
                    from models import ScrumMasters
                    scrum_master = ScrumMasters(
                        OrgID=selected_org.OrgID,
                        Email=email,
                        Name=name,
                        ContactNumber=phone_number
                    )
                    db.session.add(scrum_master)
                    db.session.commit()
                    print(f"[SUCCESS] Added {name} to ScrumMasters table")
                    
            except Exception as role_error:
                print(f"[WARNING] Failed to add user to role-specific table: {str(role_error)}")
                # Don't fail the registration if role-specific table insertion fails
            
            # ========== Send Approval Notifications ==========
            if role.lower() != "admin":
                try:
                    admins = db.session.execute(
                        db.select(Users).where(Users.Role == "admin")
                    ).scalars().all()
                    
                    for admin in admins:
                        try:
                            sm.sending_approval_req(admin, new_user)
                        except Exception as email_error:
                            print(f"[WARNING] Failed to send approval email to admin {admin.UserID}: {str(email_error)}")
                            
                except Exception as admin_error:
                    print(f"[WARNING] Failed to fetch admins for approval notification: {str(admin_error)}")
            
            flash('You successfully Signed Up!', 'success')
            return redirect(url_for('auth.login', new=True))
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] User registration failed: {str(e)}")
            print(traceback.format_exc())
            flash(f"Registration failed: {str(e)}", "error")
            return redirect(url_for('auth.add_user'))
    
    # GET request - display signup form with approved organizations
    from models import Organization
    approved_orgs = Organization.query.filter_by(Approved=True, IsActive=True).order_by(Organization.OrgName).all()
    return render_template('signup.html', organizations=approved_orgs)


@login_bp.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    print(current_user.UserName)
    log_to_csv(current_user.UserID, "Logout")
    print(current_user, "Logout")
    logout_user()
    return redirect(url_for('auth.login'))



@login_bp.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    """
    Handle OTP verification for login and password reset with comprehensive validation.
    
    GET: Display OTP verification form
    POST: Validate OTP and complete login or password reset flow
    
    Returns:
        template: OTP verification page on GET or error
        redirect: To dashboard/projects on successful login, reset password on password reset
        
    Validates:
        - OTP presence and format
        - OTP expiry time
        - OTP correctness
        - Session state validity
    """
    if request.method == 'POST':
        try:
            # Validate OTP input
            entered_otp = request.form.get('otp', '').strip()
            
            if not entered_otp:
                session['error_message'] = 'OTP is required.'
                return redirect(url_for('auth.verify_otp'))
            
            if not entered_otp.isdigit():
                session['error_message'] = 'OTP must be a number.'
                return redirect(url_for('auth.verify_otp'))
            
            if len(entered_otp) != 6:
                session['error_message'] = 'OTP must be 6 digits.'
                return redirect(url_for('auth.verify_otp'))
            
            entered_otp_int = int(entered_otp)
            
            # ========== Handle Password Reset OTP ==========
            if 'reset_otp' in session and 'reset_otp_expiry' in session:
                try:
                    reset_otp_expiry = datetime.fromisoformat(session['reset_otp_expiry'])
                    
                    # Check OTP expiry
                    if datetime.now() >= reset_otp_expiry:
                        session.pop('reset_otp', None)
                        session.pop('reset_otp_expiry', None)
                        session['error_message'] = 'OTP has expired. Please request a new one.'
                        return redirect(url_for('auth.forgot_password'))
                    
                    # Verify OTP
                    if entered_otp_int == session['reset_otp']:
                        session.pop('reset_otp')
                        session.pop('reset_otp_expiry')
                        print("[INFO] Password reset OTP verified successfully")
                        return redirect(url_for('auth.reset_password'))
                    else:
                        session['error_message'] = 'Invalid OTP. Please try again.'
                        print(f"[WARNING] Invalid password reset OTP attempted")
                        return redirect(url_for('auth.verify_otp'))
                        
                except (ValueError, TypeError) as date_error:
                    print(f"[ERROR] Invalid OTP expiry format: {str(date_error)}")
                    session.pop('reset_otp', None)
                    session.pop('reset_otp_expiry', None)
                    session['error_message'] = 'Invalid OTP session. Please try again.'
                    return redirect(url_for('auth.forgot_password'))
            
            # ========== Handle Login OTP ==========
            elif 'otp' in session and 'otp_expiry' in session:
                try:
                    otp_expiry = datetime.fromisoformat(session['otp_expiry'])
                    
                    # Check OTP expiry
                    if datetime.now() >= otp_expiry:
                        session.pop('otp', None)
                        session.pop('otp_expiry', None)
                        session.pop('username', None)
                        session.pop('role', None)
                        session.pop('uid', None)
                        session['error_message'] = 'OTP has expired. Please login again.'
                        return redirect(url_for('auth.login'))
                    
                    # Verify OTP
                    if entered_otp_int == session['otp']:
                        user_id = session.get('uid')
                        
                        if not user_id:
                            session['error_message'] = 'Invalid session. Please login again.'
                            return redirect(url_for('auth.login'))
                        
                        # Query user from database
                        user = Users.query.filter_by(UserID=user_id).first()
                        
                        if not user:
                            session['error_message'] = 'User not found. Please login again.'
                            return redirect(url_for('auth.login'))
                        
                        # Clear OTP from session
                        session.pop('otp')
                        session.pop('otp_expiry')
                        
                        # Login user with Flask-Login
                        login_user(user)
                        
                        # Log successful login
                        try:
                            log_to_csv(current_user.UserID, "Login")
                        except Exception as log_error:
                            print(f"[WARNING] Failed to log successful login: {str(log_error)}")
                        
                        print(f"[SUCCESS] User {user.UserName} logged in successfully")
                        
                        # Redirect based on role (case-insensitive check)
                        user_role = session.get('role', '').lower()
                        if user_role == 'admin':
                            return redirect(url_for('auth.admin_dashboard'))
                        else:
                            return redirect(f'/projects/{current_user.Role}/{current_user.UserID}')
                    else:
                        session['error_message'] = 'Invalid OTP. Please try again.'
                        print(f"[WARNING] Invalid login OTP attempted for user ID: {session.get('uid')}")
                        return redirect(url_for('auth.verify_otp'))
                        
                except (ValueError, TypeError) as date_error:
                    print(f"[ERROR] Invalid OTP expiry format: {str(date_error)}")
                    session.clear()
                    session['error_message'] = 'Invalid OTP session. Please login again.'
                    return redirect(url_for('auth.login'))
            
            else:
                # No OTP context in session
                session['error_message'] = 'OTP session not found. Please login or reset password again.'
                print("[WARNING] OTP verification attempted without valid session")
                return redirect(url_for('auth.login'))
                
        except Exception as e:
            print(f"[ERROR] OTP verification failed: {str(e)}")
            print(traceback.format_exc())
            session['error_message'] = 'An error occurred during OTP verification. Please try again.'
            return redirect(url_for('auth.login'))
    
    # GET request - display OTP verification form
    error_message = session.pop('error_message', None)
    return render_template('verify_otp.html', error_message=error_message)


@login_bp.route('/resend_otp', methods=['POST'])
def resend_otp():
    if 'username' in session:
        username = session['username']
        user = Users.query.filter_by(UserName=username).first()
        if user:
            otp = otp_generator()
            sm.send_otp_email(user.Email, otp)

            session['otp'] = otp
            session['otp_expiry'] = (datetime.now() + timedelta(minutes=5)).isoformat()
            session['error_message'] = 'A new OTP has been sent to your email.'
        else:
            session['error_message'] = 'User not found. Please log in again.'
    else:
        session['error_message'] = 'Session expired. Please log in again.'

    return redirect(url_for('auth.verify_otp'))


@login_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        user = Users.query.filter_by(Email=email).first()
        if not user:
            session['error_message'] = 'Email not found.'
            return redirect(url_for('auth.forgot_password'))

        otp = otp_generator()
        sm.send_otp_email(email, otp)

        session['reset_otp'] = otp
        session['reset_email'] = email
        session['reset_otp_expiry'] = (datetime.now() + timedelta(minutes=2)).isoformat()
        return redirect(url_for('auth.verify_otp'))

    error_message = session.pop('error_message', None)
    return render_template('forgot_password.html', error_message=error_message)

@login_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    """
    Handle password reset with validation and error handling.
    
    GET: Display reset password form
    POST: Validate new password, update in database
    
    Returns:
        template: Reset password page on GET or error
        redirect: To login page on success
        
    Validates:
        - New password presence and strength
        - Password confirmation match
        - Session validity (reset_email must exist)
        - User existence
    """
    if request.method == 'POST':
        try:
            # Validate inputs
            new_password = request.form.get('new_password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
            
            if not new_password:
                session['error_message'] = 'New password is required.'
                return redirect(url_for('auth.reset_password'))
            
            if not confirm_password:
                session['error_message'] = 'Please confirm your new password.'
                return redirect(url_for('auth.reset_password'))
            
            # Validate password strength
            if len(new_password) < 8:
                session['error_message'] = 'Password must be at least 8 characters long.'
                return redirect(url_for('auth.reset_password'))
            
            # Check password match
            if new_password != confirm_password:
                session['error_message'] = 'Passwords do not match.'
                return redirect(url_for('auth.reset_password'))
            
            # Validate session
            email = session.get('reset_email')
            if not email:
                session['error_message'] = 'Session expired. Please start the password reset process again.'
                print("[WARNING] Password reset attempted without valid session")
                return redirect(url_for('auth.forgot_password'))
            
            # Query user
            user = db.session.execute(
                db.select(Users).where(Users.Email == email)
            ).scalar()
            
            if not user:
                session.pop('reset_email', None)
                session['error_message'] = 'User not found. Please contact support.'
                print(f"[ERROR] User not found for email: {email}")
                return redirect(url_for('auth.login'))
            
            # Hash and update password
            hashed_password = pw.hash_password(new_password)
            user.Password = hashed_password.decode('utf-8')
            
            # Commit to database
            db.session.commit()
            print(f"[SUCCESS] Password reset successful for user: {user.UserName}")
            
            # Clear session
            session.pop('reset_email', None)
            
            flash(f"Hi {user.Name}, your password is successfully updated!", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Password reset failed: {str(e)}")
            print(traceback.format_exc())
            session['error_message'] = 'An error occurred while resetting password. Please try again.'
            return redirect(url_for('auth.reset_password'))
    
    # GET request - display reset password form
    error_message = session.pop('error_message', None)
    return render_template('reset_password.html', error_message=error_message)




@login_bp.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    user_csv_path = get_csv_path('user_history.csv')
    failed_csv_path = get_csv_path('failed_login_history.csv')
    
    df = pd.read_csv(user_csv_path, on_bad_lines='skip')
    failed_login_df = pd.read_csv(failed_csv_path, on_bad_lines='skip')

    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    failed_login_df['Timestamp'] = pd.to_datetime(failed_login_df['Timestamp'])

    df['Action'] = df['Action'].str.capitalize()

    df_logins = df[df['Action'] == 'Login']
    df_logouts = df[df['Action'] == 'Logout']

    sessions = []
    for idx, login_row in df_logins.iterrows():
        possible_logouts = df_logouts[
            (df_logouts['Username'] == login_row['Username']) &
            (df_logouts['Timestamp'] > login_row['Timestamp']) &
            (df_logouts['Timestamp'] <= login_row['Timestamp'] + pd.Timedelta(minutes=60))
        ]

        if not possible_logouts.empty:
            logout_row = possible_logouts.iloc[0]
            duration = (logout_row['Timestamp'] - login_row['Timestamp']).total_seconds() / 60
            df_logouts = df_logouts[df_logouts['Timestamp'] != logout_row['Timestamp']]
        else:
            logout_row = None
            duration = 5

        sessions.append({
            'User ID': login_row['User ID'],
            'Username': login_row['Username'],
            "Role": login_row["Role"],
            'Timestamp_login': login_row['Timestamp'],
            'Timestamp_logout': logout_row['Timestamp'] if logout_row is not None else None,
            'Duration_minutes': duration
        })

    df_sessions = pd.DataFrame(sessions)
    df_sessions['Session ID'] = df_sessions.groupby('Username').cumcount() + 1
    df_sessions['Session Number'] = df_sessions.groupby('Username').cumcount() + 1

    custom_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    bar_fig = px.bar(
        df_sessions, x="Username", y="Duration_minutes", color="Session Number",
        title="Session Duration vs. Number of Login Sessions per User",
        labels={'Session Number': 'Login Session', 'Duration_minutes': 'Session Duration (minutes)', 'Username': 'User'},
        color_discrete_sequence=custom_colors
    )
    bar_graph_html = bar_fig.to_html(full_html=False)
    login_count = df[df.Action == 'Login']['Role'].value_counts()
    pie_fig = Figure()
    pie_fig.add_trace(go.Pie(
        labels=login_count.index, values=login_count.values, textposition='outside', textinfo='percent+label'
    ))
    pie_fig.update_layout(title='User Login Distribution by Role')
    pie_graph_html = pie_fig.to_html(full_html=False)


    failed_login_df['Day'] = failed_login_df['Timestamp'].dt.day_name()
    failed_login_df['Hour'] = failed_login_df['Timestamp'].dt.hour

    heatmap_data = failed_login_df.groupby(['Day', 'Hour']).size().unstack(fill_value=0)

    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_data = heatmap_data.reindex(days_order)
    if not heatmap_data.empty and heatmap_data.size > 0:
        fig = go.Figure(
            data=go.Heatmap(
                z=heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                colorscale=custom_colors,
                colorbar=dict(title='Failed Logins')
            )
        )

        fig.update_layout(
            title='Failed Login Attempts by Time of Day and Day of Week',
            xaxis_title='Hour of Day',
            yaxis_title='Day of Week',
            xaxis=dict(tickmode='linear'),
            yaxis=dict(tickmode='linear'),
        )

        heatmap_html = fig.to_html(full_html=False)
    else:
        heatmap_html = "<p>No failed login attempts recorded.</p>"





    if request.method == 'POST':
        total_users = df_sessions['User ID'].nunique()
        total_sessions = len(df_sessions)
        avg_session_duration = df_sessions['Duration_minutes'].mean()
        role_counts = df['Role'].value_counts()

        total_roles = role_counts.sum()

        role_percentages = {role: (count / total_roles) * 100 for role, count in role_counts.items()}
        max_session_user = df_sessions.loc[df_sessions['Duration_minutes'].idxmax()]
        min_session_user = df_sessions.loc[df_sessions['Duration_minutes'].idxmin()]


        total_failed_logins = len(failed_login_df)



        most_failed_username = (
            failed_login_df["Username"].value_counts().idxmax() if not failed_login_df.empty else None
        )

        most_failed_user_count = (
            failed_login_df["Username"].value_counts().max() if not failed_login_df.empty else 0
        )
        total_login_of_users = len(df_sessions)

        failed_login_percentage = total_failed_logins * 100 / (total_failed_logins + total_login_of_users)
        print(f"Total Failed Logins: {total_failed_logins}")
        print(f"Failed Login Percentage: {failed_login_percentage}%")
        print(f"Most Failed Username: {most_failed_username}")
        print(f"Most Failed Login Attempts by a Single User: {most_failed_user_count}")
        
        overview = f"The system tracks login activities for {total_users} unique users across {total_sessions} sessions. The busiest login hour is {df['Timestamp'].dt.hour.mode()[0]}:00."
        
        detailed_insights = f"Detailed Insights:\n- Maximum session duration: {max_session_user['Duration_minutes']:.2f} minutes by {max_session_user['Username']} (Role: {max_session_user['Role']})\n- Minimum session duration: {min_session_user['Duration_minutes']:.2f} minutes by {min_session_user['Username']} (Role: {min_session_user['Role']})"
        
        failed_attempts = ""
        user = db.session.execute(db.select(Users).where(Users.UserName == most_failed_username)).scalar()
        if not user:
            most_failed_user_id = "Unknown"
        else:
            most_failed_user_id = user.UserID

        if most_failed_user_id:
            failed_attempts += f"- User with most failed logins: {most_failed_username} (User ID: {most_failed_user_id}) with {most_failed_user_count} failures"
        else:
            failed_attempts += "- No user had repeated failed login attempts."

        paragraph = "This report provides an overview of user login activity."
        summary = f"{paragraph.strip()}\n\n{overview.strip()}\n\n{detailed_insights.strip()}\n\n{failed_attempts.strip()}"


        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(200, 10, 'Login Activity Report', ln=True, align='C')
        pdf.cell(200, 10, '', ln=True)

        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, summary.strip())

        pdf_path = os.path.join('static', 'login_report.pdf')
        pdf.output(pdf_path)

        return send_file(pdf_path, as_attachment=True, mimetype='application/pdf', download_name='login_report.pdf')


    # Check if current user is admin (case-insensitive)
    if current_user.Role.lower() == 'admin':
        users = Users.query.all()
        return render_template('admin_dashboard.html', users=users, u=current_user, bar_chart=bar_graph_html, pie_chart=pie_graph_html, heatmap=heatmap_html)
    else:
        return jsonify({'error': "u don't have access to this page....."})  
 

@login_bp.route('/approve_organization/<int:org_id>', methods=['POST'])
@login_required
def approve_organization(org_id):
    """
    Approve a pending organization (Admin only).
    
    Args:
        org_id: Organization ID to approve
        
    Returns:
        redirect: Back to admin dashboard with success/error message
    """
    if current_user.Role.lower() != 'admin':
        flash("Unauthorized access. Admin privileges required.", "error")
        return redirect(url_for('team_1.dashboard'))
    
    try:
        from models import Organization
        
        # Find the organization
        organization = Organization.query.filter_by(OrgID=org_id).first()
        
        if not organization:
            flash("Organization not found.", "error")
            return redirect(url_for('auth.admin_dashboard'))
        
        if organization.Approved:
            flash(f"Organization '{organization.OrgName}' is already approved.", "warning")
            return redirect(url_for('auth.admin_dashboard'))
        
        # Approve the organization
        organization.Approved = True
        db.session.commit()
        
        flash(f"Organization '{organization.OrgName}' has been successfully approved!", "success")
        print(f"[SUCCESS] Organization approved: {organization.OrgName} (ID: {org_id})")
        
        return redirect(url_for('auth.admin_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Failed to approve organization {org_id}: {str(e)}")
        print(traceback.format_exc())
        flash(f"Failed to approve organization: {str(e)}", "error")
        return redirect(url_for('auth.admin_dashboard'))


@login_bp.route('/reject_organization/<int:org_id>', methods=['POST'])
@login_required
def reject_organization(org_id):
    """
    Reject/delete a pending organization (Admin only).
    
    Args:
        org_id: Organization ID to reject
        
    Returns:
        redirect: Back to admin dashboard with success/error message
    """
    if current_user.Role.lower() != 'admin':
        flash("Unauthorized access. Admin privileges required.", "error")
        return redirect(url_for('team_1.dashboard'))
    
    try:
        from models import Organization
        
        # Find the organization
        organization = Organization.query.filter_by(OrgID=org_id).first()
        
        if not organization:
            flash("Organization not found.", "error")
            return redirect(url_for('auth.admin_dashboard'))
        
        if organization.Approved:
            flash(f"Cannot reject approved organization '{organization.OrgName}'. Please deactivate it instead.", "warning")
            return redirect(url_for('auth.admin_dashboard'))
        
        # Check if organization has any users
        if organization.users:
            flash(f"Cannot reject organization '{organization.OrgName}' - it has {len(organization.users)} registered users.", "error")
            return redirect(url_for('auth.admin_dashboard'))
        
        org_name = organization.OrgName
        
        # Delete the organization
        db.session.delete(organization)
        db.session.commit()
        
        flash(f"Organization '{org_name}' has been rejected and removed.", "success")
        print(f"[SUCCESS] Organization rejected and deleted: {org_name} (ID: {org_id})")
        
        return redirect(url_for('auth.admin_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Failed to reject organization {org_id}: {str(e)}")
        print(traceback.format_exc())
        flash(f"Failed to reject organization: {str(e)}", "error")
        return redirect(url_for('auth.admin_dashboard'))

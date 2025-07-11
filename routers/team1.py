from flask import request, jsonify, render_template, redirect, url_for, session, Blueprint,current_app, flash
from datetime import datetime, timedelta
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



# File to store history
CSV_FILE = "user_history.csv"

login_manager = LoginManager()
login_bp = Blueprint('auth', __name__)   


# Ensure the upload folder exists
os.makedirs('static/uploads', exist_ok=True)

# Check if the file extension is allowed
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

# Initialize the CSV file if it doesn't exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["User ID","Username", "Role", "Action", "Timestamp", "IP Address"])  # Header row

# Function to log actions to CSV
def log_to_csv(user_id, action):
    user = db.session.execute(db.Select(Users).where(Users.UserID==user_id)).scalar()
    print(user.UserName, user)
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ip_address = request.remote_addr or "Unknown"
        writer.writerow([user_id, user.UserName, user.Role, action, timestamp, ip_address])


# Function to read records from the CSV file
def get_history_from_csv(user_id):
    history = []
    with open(CSV_FILE, mode='r') as file:
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
    # print(history)
    return history


@login_bp.route('/history/<int:user_id>', methods=['POST'])
def history(user_id):
    history = get_history_from_csv(user_id)
    print(history)
    return render_template('history.html', history=history)

FAILED_LOGIN_CSV_FILE = "failed_login_history.csv"


# Initialize the failed login CSV file if it doesn't exist
if not os.path.exists(FAILED_LOGIN_CSV_FILE):
    with open(FAILED_LOGIN_CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Username", "Timestamp", "IP Address"])  # Header row

# Function to log failed login attempts to a separate CSV
def log_failed_login(username):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip_address = request.remote_addr or "Unknown"
    with open(FAILED_LOGIN_CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([username, timestamp, ip_address])


### ADMIN DASHBOARD ROUTES ....


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
    approved = 'approved' in request.form  # Check if checkbox is checked
    user.Approved = approved
    db.session.commit()
    sm.user_approved(user.Email, user)
    return redirect(url_for('auth.admin_dashboard'))  




###  User Login
@login_bp.route('/', methods=['GET', 'POST'])
def login():
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Query the database to find a user by username
        user = Users.query.filter_by(UserName=username).first()
        
        
        if user and pw.verify_password(password, user.Password.encode('utf-8')):
            if not user.Approved and user.Role != 'admin':
                session['error_message'] = "Your account is not approved by the admin."
                return redirect(url_for('auth.login'))
            session.pop('error_message', None)  # Clear any previous error messages
            otp = otp_generator()
            sm.send_otp_email(user.Email, otp)

            session['otp'] = otp
            session['otp_expiry'] = (datetime.now() + timedelta(minutes=5)).isoformat()
            session['username'] = user.UserName
            session['role'] = user.Role
            session['uid']=user.UserID
            log_to_csv(user.UserID, "Login")  # Successful login
            return redirect(url_for('auth.verify_otp'))

        else:
            # Log failed login attempt to the new CSV
            log_failed_login(username)
            session['error_message'] = 'Wrong password. Please try again.'
            return redirect(url_for('auth.login'))

    error_message = session.pop('error_message', None)
    return render_template('login.html', error_message=error_message)

#####  USER REGESTRATION ....

@login_bp.route('/add_user', methods=['POST', 'GET'])
def add_user():
    if request.method == 'POST':
        # Retrieving form data
        username = request.form['username']
        email = request.form['email']
        name = request.form['name']  
        password = request.form['password']
        dob = request.form['dob']
        role = request.form.get('role')  # Optional field
        phone_number = request.form.get('phone_number')  # Optional field
        hashed_password = pw.hash_password(password)
        dob = datetime.strptime(dob, '%Y-%m-%d').date()
        approved = False
        if role.lower() == "admin":
            approved = True

        # Check if file is uploaded and is allowed
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join('static/uploads', filename)
            file.save(filepath)
        # Create a new user object
        new_user = Users(
            UserName=username,
            Password=hashed_password.decode('utf-8'),
            Email=email,
            Name=name,
            DOB=dob,
            Role=role,
            PhoneNumber=phone_number,
            Approved=approved,
            profile_picture='uploads/'+ filename
        )

        # Add and commit the new user to the database
        try:
            db.session.add(new_user)
            db.session.commit()
            admins = db.session.execute(db.select(Users).where(Users.Role == "admin")).scalars().all()
            if role != "admin":
                for admin in admins:
                    ## sending mail to admin for approval...
                    sm.sending_approval_req(admin, new_user)
            flash('You successfully Signed Up!', 'success')
            # return jsonify({'message': 'User added successfully!'}), 201
            return redirect(url_for('auth.login', new=True))
            

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    return render_template('signup.html')

#### Logout

@login_bp.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    print(current_user.UserName)
    # track_logout(None, current_user)  # Call track_login manually
    log_to_csv(current_user.UserID, "Logout")
    print(current_user, "Logout")
    logout_user()
    return redirect(url_for('auth.login'))



#### VERIFY OTP ...
@login_bp.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    
    if request.method == 'POST':
        entered_otp = request.form['otp']

        # Handle password reset OTP verification
        
        if 'reset_otp' in session and 'reset_otp_expiry' in session:
            reset_otp_expiry = datetime.fromisoformat(session['reset_otp_expiry'])
            if datetime.now() < reset_otp_expiry and int(entered_otp) == session['reset_otp']:
                session.pop('reset_otp')
                session.pop('reset_otp_expiry')
                return redirect(url_for('auth.reset_password'))  # Proceed to password reset
            else:
                session['error_message'] = 'Invalid or expired OTP for password reset.'
                return redirect(url_for('auth.verify_otp'))  # Correct route here

        # Handle login OTP verification
        elif 'otp' in session and 'otp_expiry' in session:
            otp_expiry = datetime.fromisoformat(session['otp_expiry'])
            if datetime.now() < otp_expiry and int(entered_otp) == session['otp']:
                user_id = session['uid']
                print(user_id)
                user = Users.query.filter_by(UserID=user_id).first()
                session.pop('otp')
                session.pop('otp_expiry')
                if session.get('role') == 'admin':
                    login_user(user)
                    log_to_csv(current_user.UserID, "Login")

                    # track_login(None, current_user)  # Call track_login manually

                    return redirect(url_for('auth.admin_dashboard'))  # Redirect to Admin Dashboard
                else:
                    print(user)
                    login_user(user)
                    log_to_csv(current_user.UserID, "Login")

                    # track_login(None, current_user)  # Call track_login manually

                    return redirect(f'/projects/{current_user.Role}/{current_user.UserID}')
            else:
                session['error_message'] = 'Invalid or expired OTP for login.'
                return redirect(url_for('auth.verify_otp'))  # Correct route here

        else:
            session['error_message'] = 'OTP context not found.'
            return redirect(url_for('auth.verify_otp'))  # Correct route here

    error_message = session.pop('error_message', None)
    return render_template('verify_otp.html', error_message=error_message)


# OTP Resend
@login_bp.route('/resend_otp', methods=['POST'])
def resend_otp():
    if 'username' in session:
        username = session['username']
        user = Users.query.filter_by(UserName=username).first()
        if user:
            # Generate a new OTP
            otp = otp_generator()
            sm.send_otp_email(user.Email, otp)

            session['otp'] = otp
            session['otp_expiry'] = (datetime.now() + timedelta(minutes=5)).isoformat()
            session['error_message'] = 'A new OTP has been sent to your email.'
        else:
            session['error_message'] = 'User not found. Please log in again.'
    else:
        session['error_message'] = 'Session expired. Please log in again.'

    return redirect(url_for('auth.verify_otp'))  # Correct route here


# Forgot Password
@login_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        # Check if email exists in the database
        user = Users.query.filter_by(Email=email).first()
        if not user:
            session['error_message'] = 'Email not found.'
            return redirect(url_for('auth.forgot_password'))  # Correct route here

        # Generate OTP and store it in session
        otp = otp_generator()
        sm.send_otp_email(email, otp)

        session['reset_otp'] = otp
        session['reset_email'] = email
        session['reset_otp_expiry'] = (datetime.now() + timedelta(minutes=2)).isoformat()
        return redirect(url_for('auth.verify_otp'))  # Correct route here

    error_message = session.pop('error_message', None)
    return render_template('forgot_password.html', error_message=error_message)

# Reset Password
@login_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            session['error_message'] = 'Passwords do not match.'
            return redirect(url_for('auth.reset_password'))  # Correct route here

        email = session.get('reset_email')
        if not email:
            return jsonify({'error': 'Session expired. Start the process again.'}), 400

        # Update the password in the database
        user = db.session.execute(db.select(Users).where(Users.Email == email)).scalar()
        user_id = user.UserID
        if not user:
            return jsonify({'error': 'User not found.'}), 404
        
        hashed_password = pw.hash_password(new_password)
        user.Password = hashed_password.decode('utf-8')
        db.session.commit()

        session.pop('reset_email')
        # return jsonify({'message': f'Hi, {user.Name} ur Password reset successfully! for {user_id}'}), 200
        flash(f"Hi {user.Name} ,your password is successfully updated ")
        return redirect(url_for('auth.login'))

    error_message = session.pop('error_message', None)
    return render_template('reset_password.html', error_message=error_message)


### ADMIN DASHBOARD .......


@login_bp.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    # print(current_user.Name)
    # Load data
    df = pd.read_csv('user_history.csv', on_bad_lines='skip')
    failed_login_df = pd.read_csv('failed_login_history.csv', on_bad_lines='skip')  # Skip problematic rows

    # Convert Timestamp to datetime
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    failed_login_df['Timestamp'] = pd.to_datetime(failed_login_df['Timestamp'])

    # Normalize the Action column to consistent case
    df['Action'] = df['Action'].str.capitalize()

    # Separate login and logout rows
    df_logins = df[df['Action'] == 'Login']
    df_logouts = df[df['Action'] == 'Logout']

    # Initialize empty list to store sessions
    sessions = []
    for idx, login_row in df_logins.iterrows():
        # Find logouts after this login within 60 minutes
        possible_logouts = df_logouts[
            (df_logouts['Username'] == login_row['Username']) & 
            (df_logouts['Timestamp'] > login_row['Timestamp']) & 
            (df_logouts['Timestamp'] <= login_row['Timestamp'] + pd.Timedelta(minutes=60))
        ]
        
        if not possible_logouts.empty:
            # Get the first matching logout
            logout_row = possible_logouts.iloc[0]
            duration = (logout_row['Timestamp'] - login_row['Timestamp']).total_seconds() / 60
            # Remove used logout to avoid duplicate pairing
            df_logouts = df_logouts[df_logouts['Timestamp'] != logout_row['Timestamp']]
        else:
            # No logout found within 60 minutes, set default duration to 5 minutes
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

    # Create DataFrame for sessions
    df_sessions = pd.DataFrame(sessions)
    df_sessions['Session ID'] = df_sessions.groupby('Username').cumcount() + 1
    df_sessions['Session Number'] = df_sessions.groupby('Username').cumcount() + 1

    # Bar Chart
    custom_colors = ['#F25C54', '#6B8E23', '#3B9A8C', '#FFB6B9', '#FF6F61', '#6A5ACD', '#FFD700', '#008080']
    bar_fig = px.bar(
        df_sessions, x="Username", y="Duration_minutes", color="Session Number",
        title="Session Duration vs. Number of Login Sessions per User",
        labels={'Session Number': 'Login Session', 'Duration_minutes': 'Session Duration (minutes)', 'Username': 'User'},
        color_discrete_sequence=custom_colors
    )
    bar_graph_html = bar_fig.to_html(full_html=False)
    # Pie Chart
    login_count = df[df.Action == 'Login']['Role'].value_counts()
    pie_fig = Figure()
    pie_fig.add_trace(go.Pie(
        labels=login_count.index, values=login_count.values, textposition='outside', textinfo='percent+label'
    ))
    pie_fig.update_layout(title='User Login Distribution by Role')
    pie_graph_html = pie_fig.to_html(full_html=False)

    # import plotly.graph_objects as go
    # import pandas as pd

    # Ensure 'Day' and 'Hour' columns are created
    failed_login_df['Day'] = failed_login_df['Timestamp'].dt.day_name()
    failed_login_df['Hour'] = failed_login_df['Timestamp'].dt.hour

    # Group data by 'Day' and 'Hour', and count occurrences
    heatmap_data = failed_login_df.groupby(['Day', 'Hour']).size().unstack(fill_value=0)

    # Reorder days of the week
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_data = heatmap_data.reindex(days_order)
    # print(heatmap_data)
    # Create the heatmap using Plotly
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

        # Convert Plotly figure to HTML
        heatmap_html = fig.to_html(full_html=False)
    else:
        heatmap_html = "<p>No failed login attempts recorded.</p>"

    # The variable `heatmap_html` contains the heatmap in HTML format for rendering in a web application.



    ### EXPORTING DATA INTO PDF  ...

    if request.method == 'POST':
        # Generate aggregated statistics
        total_users = df_sessions['User ID'].nunique()
        total_sessions = len(df_sessions)
        avg_session_duration = df_sessions['Duration_minutes'].mean()
        # Calculate the role counts
        role_counts = df['Role'].value_counts()

        # Calculate the total number of roles (this is used to calculate the percentage)
        total_roles = role_counts.sum()

        # Calculate the percentage of each role
        role_percentages = {role: (count / total_roles) * 100 for role, count in role_counts.items()}
        # Assuming session_df has been created
        max_session_user = df_sessions.loc[df_sessions['Duration_minutes'].idxmax()]
        min_session_user = df_sessions.loc[df_sessions['Duration_minutes'].idxmin()]
        
        # failed login ....
        # Load failed login data
        # failed_login_df = pd.read_csv('failed_login_history.csv')

        # Calculate the total number of failed login attempts
        total_failed_logins = len(failed_login_df)

       

        # Identify the username with the most failed logins
        most_failed_username = (
            failed_login_df["Username"].value_counts().idxmax() if not failed_login_df.empty else None
        )

        # Count of the most failed login attempts for the username
        most_failed_user_count = (
            failed_login_df["Username"].value_counts().max() if not failed_login_df.empty else 0
        )
         # Calculate the percentage of failed logins (relative to the total rows in the DataFrame)
        # In this case, all rows are failed logins, so the percentage is 100%.
        # print(df_sessions)
        total_login_of_users = len(df_sessions)
        
        failed_login_percentage = total_failed_logins * 100 / (total_failed_logins + total_login_of_users)
        # Print the results
        print(f"Total Failed Logins: {total_failed_logins}")
        print(f"Failed Login Percentage: {failed_login_percentage}%")
        print(f"Most Failed Username: {most_failed_username}")
        print(f"Most Failed Login Attempts by a Single User: {most_failed_user_count}")
        # Generate summary paragraph
        # Generate overview
        # Generate overview
        overview = f"""
        The system tracks login activities for {total_users} unique users across {total_sessions} sessions.
        The busiest login hour is {df['Timestamp'].dt.hour.mode()[0]}:00.
        """

        # Add role distribution
        overview += "\n- Role distribution:\n"
        for role, percentage in role_percentages.items():
            overview += f"  {role}: {role_counts[role]} ({percentage:.1f}%)\n"

        # Add a paragraph to explain the context
        paragraph = f"""
        In total, the system has recorded login data from a wide range of users, with {total_users} unique individuals participating across {total_sessions} sessions. 
        This data offers valuable insights into user behavior, including session lengths, peak login times, and the distribution of roles within the system. 
        The role distribution gives an understanding of how the user base is segmented, while the analysis of login behavior helps identify patterns that can inform system optimizations.
        """

        # Generate detailed insights
        detailed_insights = f"""
        Detailed Insights:
        - Maximum session duration: {max_session_user['Duration_minutes']:.2f} minutes by {max_session_user['Username']} (Role: {max_session_user['Role']})
        - Minimum session duration: {min_session_user['Duration_minutes']:.2f} minutes by {min_session_user['Username']} (Role: {min_session_user['Role']})
        """

        # Add failed login insights
        failed_attempts = f"""
        - Total failed login attempts: {total_failed_logins} ({failed_login_percentage:.2f}% of all actions)
        """
        
        user = db.session.execute(db.select(Users).where(Users.UserName == most_failed_username)).scalar()
        if not user:
            most_failed_user_id = "Unknown"
        else:
            most_failed_user_id = user.UserID

        if most_failed_user_id:
            failed_attempts += f"- User with most failed logins: {most_failed_username} (User ID: {most_failed_user_id}) with {most_failed_user_count} failures"
        else:
            failed_attempts += "- No user had repeated failed login attempts."

        # Combine sections for display or export
        summary = f"{paragraph.strip()}\n\n{overview.strip()}\n\n{detailed_insights.strip()}\n\n{failed_attempts.strip()}"

        
                # Generate the PDF report
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(200, 10, 'Login Activity Report', ln=True, align='C')
        pdf.cell(200, 10, '', ln=True)  # Empty line

        # Add summary paragraph
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, summary.strip())

        # Save PDF
        pdf_path = os.path.join('static', 'login_report.pdf')
        pdf.output(pdf_path)

        return send_file(pdf_path, as_attachment=True, mimetype='application/pdf', download_name='login_report.pdf')


    if current_user.Role == 'admin':
        users = Users.query.all()
        return render_template('admin_dashboard.html', users=users, u=current_user, bar_chart=bar_graph_html, pie_chart=pie_graph_html, heatmap=heatmap_html)
    else:
        return jsonify({'error': "u don't have access to this page....."})
    



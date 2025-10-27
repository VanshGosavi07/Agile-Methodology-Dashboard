from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
import smtplib
from email.mime.text import MIMEText
from email.message import EmailMessage
import os
import smtplib
from email import encoders

# Email Configuration - Gmail
SENDER_EMAIL = "vanshgosavi777@gmail.com"
SENDER_PASSWORD = "pfry ijwv scdb pcio"

def send_otp_email(email, otp):
    subject = 'Your OTP Code'
    body = f'Your OTP code is: {otp}'


    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())
    except Exception as e:
        print(f'Error sending email: {str(e)}')

def approval_status_mail(email, name):
    subject = f'Hi, {name}  '
    body = f'{name} , Your registration is not approved by Admin. \nWait till admin approval after that u can login to ur account.\n\nor u can contact admin...\nThank YOu..'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())
    except Exception as e:
        print(f'Error sending email: {str(e)}')

def sending_approval_req(admin, user):
    subject = f'A new user {user.Name} has signed up '
    body = f'Hi {admin.Name},\nA new user {user.Name} with user id - {user.UserID} is signed up. \nPlease approve their registration so that he can access the Dashboard.'

    print(body)
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = admin.Email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, admin.Email, msg.as_string())
    except Exception as e:
        print(f'Error sending email: {str(e)}')

def user_deleted(email, user):
    subject = f'Hi, {user.UserName}  '
    body = f'{user.UserName} ,  \nYour ur registration is removed ...!!'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())
    except Exception as e:
        print(f'Error sending email: {str(e)}')

def user_approved(email, user):
    subject = f'Hi, {user.UserName}  '
    body = f'{user.UserName} ,  \nYour  registration is approved by Admin ...!!\nNow u can login to ur Account\n\nThank YOu...!'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())
    except Exception as e:
        print(f'Error sending email: {str(e)}')




def send_emails_to_users(email_list, project_name, proj_desc, roles):
    sender_email = "sukheshdasari@gmail.com"
    sender_password = "drerssxnyxukxwlz"
    subject = "Project Assignment Notification"

    try:
        for recipient_email, role in zip(email_list, roles):
            msg = EmailMessage()
            body_template = (
                f"Hello,\n\nYou have assigned {role},\n\n"
                f"You have been assigned to a new project: {project_name}.\n"
                "Please log in to the system for more details.\n\n"
                f"Description of project:{proj_desc}\n\n"
                "Regards,\nProject Management Team"
            )
            msg["From"] = sender_email
            msg["To"] = recipient_email
            msg["Subject"] = subject
            msg.set_content(body_template)

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)

            print(f"Email sent to {recipient_email}!")

    except Exception as e:
        print(f"Failed to send email: {e}")



def send_proj_assign_info(email_list, project_name,proj_desc,roles):
    sender_email = SENDER_EMAIL
    sender_password = SENDER_PASSWORD
    subject = "Project Assignment Notification"


    try:
        for recipient_email, role in zip(email_list, roles):
            msg = EmailMessage()
            body_template = (
            f"Hello,\n\nYou have assigned {role},\n\n"
            f"You have been assigned to a new project: {project_name}.\n"
            "Please log in to the system for more details.\n\n"
            f"Description of project:{proj_desc}\n\n"
            "Regards,\nProject Management Team"
            )
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.set_content(body_template)

            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)

            print(f"Email sent to {recipient_email}!")

    except Exception as e:
        print(f"Failed to send email: {e}")


def send_email_with_report(report_type, file_path):
    try:
        sender_email = SENDER_EMAIL
        sender_password = SENDER_PASSWORD
        recipient_email = "examplenamez543@gmail.com"

        latest_report = file_path

        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        subject = f"{report_type} Report - {current_datetime}"
        body = f"Hello,\n\nPlease find the attached {report_type.lower()} report.\n\nBest regards,\nAgile Dashboard Team"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))
        with open(latest_report, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={os.path.basename(latest_report)}'
            )
            msg.attach(part)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print(f"Email sent successfully with the report: {os.path.basename(latest_report)}")

    except Exception as e:
        print(f"An error occurred while sending the email: {e}")
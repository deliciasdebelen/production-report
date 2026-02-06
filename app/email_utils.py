import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(subject, body, recipients, is_html=False):
    """
    Sends an email to the specified recipients.
    """
    if not recipients:
        print("No recipients provided.")
        return

    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    if not smtp_user or not smtp_password:
        print("SMTP Credentials not found. Skipping email send.")
        print(f"--- FAKE EMAIL ---")
        print(f"To: {recipients}")
        print(f"Subject: {subject}")
        print(f"Body: {body[:100]}...")
        print("------------------")
        return

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject

    if is_html:
        msg.attach(MIMEText(body, 'html'))
    else:
        msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipients, msg.as_string())
        server.quit()
        print(f"Email sent to {recipients}")
    except Exception as e:
        print(f"Failed to send email: {e}")

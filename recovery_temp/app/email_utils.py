import smtplib
import os
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.database import SessionLocal
from app import models

def send_email(subject, body, recipients, is_html=False):
    """
    Sends an email to the specified recipients and logs the outcome in the database.
    """
    if not recipients:
        print("No recipients provided.")
        return

    db = SessionLocal()
    
    # Default settings for the log
    recipients_str = ", ".join(recipients)
    log_entry = models.EmailLog(
        recipients=recipients_str,
        subject=subject,
        status="Failed", # default to failed unless success
        error_message=""
    )

    try:
        settings = db.query(models.SupportSettings).first()
        smtp_server = settings.smtp_server if settings and settings.smtp_server else os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = settings.smtp_port if settings and settings.smtp_port else int(os.getenv("SMTP_PORT", "587"))
        smtp_user = settings.smtp_user if settings and settings.smtp_user else os.getenv("SMTP_USER", "")
        smtp_password = settings.smtp_password if settings and settings.smtp_password else os.getenv("SMTP_PASSWORD", "")

        if not smtp_user or not smtp_password:
            msg = "SMTP Credentials not found. Skipping email send."
            print(msg)
            print(f"--- FAKE EMAIL ---\nTo: {recipients_str}\nSubject: {subject}\nBody: {body[:100]}...\n------------------")
            log_entry.status = "Failed"
            log_entry.error_message = msg
            db.add(log_entry)
            db.commit()
            return

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipients_str
        msg['Subject'] = subject

        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipients, msg.as_string())
        server.quit()
        
        print(f"Email sent to {recipients}")
        log_entry.status = "Sent"
        log_entry.error_message = None
        db.add(log_entry)
        db.commit()

    except Exception as e:
        print(f"Failed to send email: {e}")
        log_entry.status = "Failed"
        log_entry.error_message = str(e) + "\n" + traceback.format_exc()
        db.add(log_entry)
        db.commit()
    finally:
        db.close()

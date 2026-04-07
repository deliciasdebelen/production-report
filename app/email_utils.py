import smtplib
import os
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.database import SessionLocal
from app import models

# Timeout máximo para la conexión SMTP (segundos)
SMTP_TIMEOUT = 10


def send_email(subject, body, recipients, is_html=False):
    """
    Envía un email a los destinatarios indicados y registra el resultado en BD.
    Diseñada para ejecutarse en background (BackgroundTasks) — nunca bloquea la respuesta HTTP.
    """
    if not recipients:
        print("No recipients provided.")
        return

    db = SessionLocal()
    recipients_str = ", ".join(recipients)
    log_entry = models.EmailLog(
        recipients=recipients_str,
        subject=subject,
        status="Failed",
        error_message=""
    )

    try:
        settings = db.query(models.SupportSettings).first()
        smtp_server  = (settings.smtp_server  if settings and settings.smtp_server  else None) or os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port    = (settings.smtp_port    if settings and settings.smtp_port    else None) or int(os.getenv("SMTP_PORT", "587"))
        smtp_user    = (settings.smtp_user    if settings and settings.smtp_user    else None) or os.getenv("SMTP_USER", "")
        smtp_password = (settings.smtp_password if settings and settings.smtp_password else None) or os.getenv("SMTP_PASSWORD", "")

        if not smtp_user or not smtp_password:
            msg = "SMTP Credentials not configured. Email not sent."
            print(msg)
            print(f"--- EMAIL SIMULADO ---\nPara: {recipients_str}\nAsunto: {subject}\n---")
            log_entry.status = "Skipped"
            log_entry.error_message = msg
            db.add(log_entry)
            db.commit()
            return

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipients_str
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html' if is_html else 'plain'))

        # Timeout evita que smtplib cuelgue indefinidamente
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=SMTP_TIMEOUT)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipients, msg.as_string())
        server.quit()

        print(f"Email enviado a {recipients_str}")
        log_entry.status = "Sent"
        log_entry.error_message = None
        db.add(log_entry)
        db.commit()

    except smtplib.SMTPException as e:
        print(f"SMTP error al enviar email: {e}")
        log_entry.status = "Failed"
        log_entry.error_message = f"SMTPException: {e}"
        db.add(log_entry)
        db.commit()

    except TimeoutError as e:
        print(f"Timeout conectando al servidor SMTP: {e}")
        log_entry.status = "Failed"
        log_entry.error_message = f"SMTP Timeout ({SMTP_TIMEOUT}s): {e}"
        db.add(log_entry)
        db.commit()

    except Exception as e:
        print(f"Error inesperado enviando email: {e}")
        log_entry.status = "Failed"
        log_entry.error_message = str(e) + "\n" + traceback.format_exc()
        db.add(log_entry)
        db.commit()

    finally:
        db.close()

import paramiko
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import ProfitAutomationConfig
import datetime
import traceback

OPENCLAW_PROMPT = """Abre la herramienta administrativa Profit Plus.
Ve a la pestaña Inventario y ejecuta la tarea 'Traslados - monto a distribuir'. Suma renglones.
Luego ejecuta 'Integridad de lotes'.
Para ambas debes asegurarte de tildar siempre la opción 'Corregir automáticamente'.
Realiza este proceso exactamente 3 veces.

Luego ve a la pestaña 'Stock'.
Ejecuta las validaciones de consistencias de las siguientes variables (tildando siempre 'Corregir automáticamente' en cada iteración):
1. Actual - Principal
2. Actual - Secundario
3. Por llegar - Principal
4. Por llegar - Secundario
5. Comprometido - Principal
6. Comprometido - Secundario
7. Por despachar - Principal
8. Por despachar - Secundario

Luego ejecuta la validación 'Stock de Lotes' (tildando 'Corregir automáticamente').
Repite este proceso entero de la pestaña Stock exactamente 3 veces.
Asegúrate de seguir este orden estrictamente."""

# Email Settings
SMTP_SERVER = "server42.web-hosting.com" # Generally use the cPanel server hostname or mail.deliciasdebelen.com
SMTP_PORT = 465
SMTP_USER = "notificaciones@deliciasdebelen.com"
SMTP_PASS = "B3l3n*2026"

scheduler = BackgroundScheduler()

def send_email_notification(to_addresses, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = to_addresses
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        # Uncomment if server is custom
        # server = smtplib.SMTP(SMTP_SERVER, 587)
        # server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [e.strip() for e in to_addresses.split(',')], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        traceback.print_exc()
        return False

def execute_openclaw_task():
    print(f"[{datetime.datetime.now()}] Starting OpenClaw execution...")
    try:
        # Establish SSH using paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('192.168.1.193', username='administrador', password='GRW7czL3*')
        
        # We need to escape the prompt properly to pass to bash, or create a temp file.
        import base64
        b64_prompt = base64.b64encode(OPENCLAW_PROMPT.encode('utf-8')).decode('utf-8')
        
        # Command to create a file, decode it, and run openclaw
        cmd = f'''
        echo {b64_prompt} | base64 -d > /tmp/openclaw_profit_prompt.txt
        export PATH=$PATH:$HOME/.nvm/versions/node/v22.14.0/bin
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh"
        openclaw run "$(< /tmp/openclaw_profit_prompt.txt)"
        '''
        
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        
        ssh.close()
        
        return {
            "success": exit_status == 0,
            "stdout": out,
            "stderr": err,
            "prompt_used": OPENCLAW_PROMPT
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

def scheduled_job():
    db = SessionLocal()
    config = db.query(ProfitAutomationConfig).first()
    
    if not config or not config.is_active:
        print("Automation is disabled or config not found. Skipping.")
        db.close()
        return
        
    emails = config.emails
    db.close()
    
    result = execute_openclaw_task()
    
    # Format the email body
    if result.get("success"):
        subject = "✅ Éxito: Automatización de Profit Plus Completada"
        body = f"La automatización de Profit Plus finalizó correctamente.\n\n"
        body += f"Resultados de OpenClaw:\n{result.get('stdout', '')}\n"
    else:
        subject = "❌ Error: Inicialización de Automatización de Profit Plus"
        body = f"Ocurrió un error al ejecutar OpenClaw.\n\n"
        body += f"Error:\n{result.get('error', '')}\n{result.get('stderr', '')}\n\nTraceback:\n{result.get('traceback', '')}"
        
    send_email_notification(emails, subject, body)

def get_db_cron_schedule():
    db = SessionLocal()
    config = db.query(ProfitAutomationConfig).first()
    db.close()
    if config and config.cron_schedule:
        return config.cron_schedule
    return "0 8-18/1 * * 1-5" # Fallback: Every hour from 8 to 18 (default format we can parse simply)

def setup_scheduler():
    # Only try to setup if the table exists
    try:
        cron_expr = get_db_cron_schedule()
        # Parse basic cron string. Expected "Minute Hour Dom Month Dow"
        parts = cron_expr.strip().split()
        if len(parts) == 5:
            min, hr, dom, mth, dow = parts
            scheduler.add_job(
                scheduled_job,
                CronTrigger(minute=min, hour=hr, day=dom, month=mth, day_of_week=dow),
                id='profit_automation',
                replace_existing=True
            )
            scheduler.start()
            print(f"Profit Automation Scheduler started with CRON {cron_expr}")
        else:
            print("Invalid CRON format in database. Expected 5 parts.")
    except Exception as e:
        print(f"Could not setup automation scheduler: {e}")

def update_scheduler_cron(new_cron: str):
    parts = new_cron.strip().split()
    if len(parts) == 5:
        min, hr, dom, mth, dow = parts
        scheduler.reschedule_job(
            'profit_automation',
            trigger=CronTrigger(minute=min, hour=hr, day=dom, month=mth, day_of_week=dow)
        )
        print(f"Scheduler job updated to {new_cron}")
    else:
        raise ValueError("Invalid cron format")

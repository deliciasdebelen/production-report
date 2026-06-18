import paramiko
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import MismatchAutomationConfig
from .automation_scheduler import scheduler, send_email_notification
import datetime
import traceback

OPENCLAW_PROMPT = """Ejecuta una revisión en la base de datos SQL Server 'carmal_a' del servidor 192.168.1.205.
Debes buscar y reportar discrepancias en dos casos específicos de hoy o días recientes:
1. En la tabla saDevolucionCliente, verifica si la suma de los montos de sus renglones (saDevolucionClienteReng) no coincide con el subtotal, total neto, total bruto o IVA del documento cabecera.
2. En la tabla saNotaCreditoCliente originadas por devoluciones, verifica si poseen un "saldo" erróneo mayor a 0 que genera diferencias.

Si encuentras alguna de estas inconsistencias de descuadre de inventario/facturación debido a los triggers, genera un reporte detallado mencionando los números de documento afectados ('doc_num'), los montos esperados y los montos reales errados. Si no hay inconsistencias, responde 'Todo correcto, sin discrepancias encontradas.'"""

def execute_openclaw_mismatch_task():
    print(f"[{datetime.datetime.now()}] Starting OpenClaw Mismatch revision...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('192.168.1.193', username='administrador', password='GRW7czL3*')
        
        import base64
        b64_prompt = base64.b64encode(OPENCLAW_PROMPT.encode('utf-8')).decode('utf-8')
        
        cmd = f'''
        echo {b64_prompt} | base64 -d > /tmp/openclaw_mismatch_prompt.txt
        export PATH=$PATH:$HOME/.nvm/versions/node/v22.14.0/bin
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh"
        openclaw run "$(< /tmp/openclaw_mismatch_prompt.txt)"
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

def scheduled_mismatch_job():
    db = SessionLocal()
    config = db.query(MismatchAutomationConfig).first()
    
    if not config or not config.is_active:
        print("Mismatch Automation is disabled or config not found. Skipping.")
        db.close()
        return
        
    emails = config.emails
    db.close()
    
    result = execute_openclaw_mismatch_task()
    
    if result.get("success"):
        subject = "📊 Reporte: Revisión de Inconsistencias (Devoluciones/NCR)"
        body = f"La validación diaria de descuadres en Profit Plus finalizó.\n\n"
        body += f"Reporte del Agente OpenClaw:\n{result.get('stdout', '')}\n"
    else:
        subject = "❌ Error: Inicialización de Revisión de Discrepancias"
        body = f"Ocurrió un error al ejecutar el agente de revisión.\n\n"
        body += f"Error:\n{result.get('error', '')}\n{result.get('stderr', '')}"
        
    send_email_notification(emails, subject, body)

def get_mismatch_db_cron_schedule():
    db = SessionLocal()
    config = db.query(MismatchAutomationConfig).first()
    db.close()
    if config and config.cron_schedule:
        return config.cron_schedule
    return "30 7,12 * * *" 

def setup_mismatch_scheduler(scheduler):
    try:
        cron_expr = get_mismatch_db_cron_schedule()
        parts = cron_expr.strip().split()
        if len(parts) == 5:
            min, hr, dom, mth, dow = parts
            scheduler.add_job(
                scheduled_mismatch_job,
                CronTrigger(minute=min, hour=hr, day=dom, month=mth, day_of_week=dow),
                id='mismatch_automation',
                replace_existing=True
            )
            print(f"Mismatch Automation Scheduler started with CRON {cron_expr}")
        else:
            print("Invalid CRON format in database for mismatch. Expected 5 parts.")
    except Exception as e:
        print(f"Could not setup mismatch scheduler: {e}")

def update_mismatch_scheduler_cron(scheduler, new_cron: str):
    parts = new_cron.strip().split()
    if len(parts) == 5:
        min, hr, dom, mth, dow = parts
        scheduler.reschedule_job(
            'mismatch_automation',
            trigger=CronTrigger(minute=min, hour=hr, day=dom, month=mth, day_of_week=dow)
        )
        print(f"Mismatch Scheduler job updated to {new_cron}")
    else:
        raise ValueError("Invalid cron format")

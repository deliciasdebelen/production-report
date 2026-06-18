import paramiko
import base64
import datetime
import traceback
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import SupportSettings, AudiLog
from .automation_scheduler import scheduler, send_email_notification

AUDI_PROMPT = """Eres 'Audi', una Inteligencia Artificial operando en sistemas integrados de OpenClaw. Eres experta en la auditoría de logística e inventarios en bases de datos Profit Plus MSSQL.
Tu misión diaria es evaluar la salud y las excepciones del almacén 'P1-PT'.

Realiza y evalúa este mandato:
Lanza tu propia revisión vía SQL directa en el servidor '192.168.1.48' identificando lo siguiente:
1. Existen documentos de tipo "AJUS" que ocasionan totales de lote teóricamente negativos. Debes revisar si hay lotes en 'saLoteEntrada' vinculados a 'P1-PT' cuyo inventario total ('Stock_Actual') marca exactamente CERO ('0.00'), pero que cruzados internamente con 'saLoteSalida' indican consumos que los superan, evidenciando que el sistema o su 'CHECK CONSTRAINT' bloqueó la resta dejándolos en cero a la fuerza. 
2. Busca si en 'saLoteSalida' hay consumos de lotes que quedaron estrictamente huérfanos sin rastro original en 'saLoteEntrada'. 

Instrucciones para generar informe (Tone: Analítico y profesional):
- Formula un informe detallando todos los lotes con estas inconsistencias precisas si las detectas. Detalla los lotes.
- Si un lote particular no existe en saLoteEntrada repórtalo como un "Error logico Crítico (Lote inexistente de origen)".
- Si compruebas que el inventario de Lotes se ha conciliado o reparado satisfactoriamente (ya no encuentras descuadres en la verificación), reporta firmemente: 'El inventario de Lotes en P1-PT fue completamente conciliado y está exento de restricciones falsas por Constraint.'

Crea tu informe de salida en base a estas instrucciones con formato Markdown limpio."""

def execute_openclaw_audi_task():
    print(f"[{datetime.datetime.now()}] Iniciando a Audi (Agente de Auditoria de Lotes P1-PT)...")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('192.168.1.193', username='administrador', password='GRW7czL3*')
        
        b64_prompt = base64.b64encode(AUDI_PROMPT.encode('utf-8')).decode('utf-8')
        
        cmd = f'''
        echo {b64_prompt} | base64 -d > /tmp/openclaw_audi_prompt.txt
        export PATH=$PATH:$HOME/.nvm/versions/node/v22.14.0/bin
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh"
        openclaw run "$(< /tmp/openclaw_audi_prompt.txt)"
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
            "prompt_used": AUDI_PROMPT
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

def scheduled_audi_job():
    db = SessionLocal()
    settings = db.query(SupportSettings).first()
    # Usar las notificaciones globales si existen o un default corporativo
    emails = settings.notification_emails if settings and settings.notification_emails else "notificaciones@deliciasdebelen.com"
    db.close()
    
    result = execute_openclaw_audi_task()
    
    # Analyze status basically based on keywords or if success
    log_status = "Conciliado" if "exento" in str(result.get('stdout', '')).lower() else "Con Discrepancias"
    
    # Save to db
    db = SessionLocal()
    new_log = AudiLog(report_text=result.get("stdout", ""), status=log_status)
    db.add(new_log)
    db.commit()
    db.close()

    if result.get("success"):
        subject = "📊 Informe Diario de I.A Audi: Auditoría Lotes P1-PT vs Restricción MSSQL"
        body = f"Notificación Automática del Sistema IA: Audi ha finalizado su investigación diaria de inventarios.\n\n"
        body += f"--- {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n\n"
        body += f"{result.get('stdout', '')}\n"
    else:
        subject = "❌ Error: Operatividad IA Audi - Falla Analítica"
        body = f"Ocurrió un error al invocar la rutina de Audi (OpenClaw) en el servidor proxy.\n\n"
        body += f"Detalles Críticos:\n{result.get('error', '')}\n{result.get('stderr', '')}"
        
    send_email_notification(emails, subject, body)

def setup_audi_scheduler(scheduler):
    try:
        # Se ejecuta diariamente a las 8:30 AM
        scheduler.add_job(
            scheduled_audi_job,
            CronTrigger(minute='30', hour='8', day='*', month='*', day_of_week='*'),
            id='audi_automation_p1_pt',
            replace_existing=True
        )
        print("💡 IA AUDI Programada exitosamente para arrancar auditorías [CRON: 30 8 * * *]")
    except Exception as e:
        print(f"❌ Error acoplando IA Audi al subsistema Scheduler: {e}")

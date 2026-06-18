from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import datetime
import logging
from app.database import SessionLocal, sqlsrv_engine
from app.models import ConsistencyLog
import uuid
import json

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

PROCEDURES = [
    "pValidarTrasladoMontoDistribuidoTotal",
    "pValidarTrasladoMontoDistribuidoProrateo",
    "pValidarLoteDocumentoConLote",
    "pValidarLoteDocumentoSinLote",
    "pValidarLoteEntradaDatos",
    "pValidarLoteEntradaNoOrigen",
    "pValidarLoteEntradaSalidaDatos",
    "pValidarLoteSalidaDatos",
    "pValidarStockAct",
    "pValidarSStockAct",
    "pValidarStockLle",
    "pValidarSStockLle",
    "pValidarStockCom",
    "pValidarSStockCom",
    "pValidarStockDes",
    "pValidarSStockDes",
    "pValidarLoteStock"
]

def run_consistency_check(b_corregir: int, initiated_by: str):
    """
    Runs all consistency stored procedures and logs results to PostgreSQL.
    """
    logger.info(f"Starting consistency validation (bCorregir={b_corregir}, initiated_by={initiated_by})")
    start_time = datetime.datetime.now()
    
    results = []
    overall_status = "SUCCESS"
    
    try:
        with sqlsrv_engine.connect() as conn:
            raw_conn = conn.connection.dbapi_connection
            cursor = raw_conn.cursor()
            
            # Execute procedures in 2 passes
            for pass_num in [1, 2]:
                for proc in PROCEDURES:
                    proc_start = datetime.datetime.now()
                    id_process = str(uuid.uuid4()).upper()
                    
                    temp_motivos = []
                    proc_status = "SUCCESS"
                    try:
                        cursor.execute(f"EXEC {proc} @bCorregir = {b_corregir}, @IdProcess = '{id_process}'")
                        
                        while True:
                            try:
                                rows = cursor.fetchall()
                                for r in rows:
                                    if r[0]:
                                        temp_motivos.append(str(r[0]))
                            except:
                                pass
                            if not cursor.nextset():
                                break
                    except Exception as ex:
                        proc_status = "FAILED"
                        overall_status = "FAILED"
                        temp_motivos.append(str(ex))
                        
                    duration = (datetime.datetime.now() - proc_start).total_seconds()
                    
                    results.append({
                        "proc_name": proc,
                        "pass_number": pass_num,
                        "status": proc_status,
                        "duration_seconds": duration,
                        "motivos": temp_motivos if temp_motivos else ["Sin novedades"]
                    })
                    
            raw_conn.commit()
            cursor.close()
            
    except Exception as e:
        logger.error(f"Error running consistency checks: {e}")
        overall_status = "FAILED"
        results.append({
            "error": str(e)
        })
        
    duration_overall = (datetime.datetime.now() - start_time).total_seconds()
    
    # Save log to PostgreSQL
    db = SessionLocal()
    try:
        log_entry = ConsistencyLog(
            execution_date=datetime.datetime.now(),
            initiated_by=initiated_by,
            status=overall_status,
            details=json.dumps(results),
            duration_seconds=duration_overall
        )
        db.add(log_entry)
        db.commit()
        logger.info(f"Consistency validation completed in {duration_overall}s. Log saved with ID {log_entry.id}")
    except Exception as e:
        logger.error(f"Error saving log to PostgreSQL: {e}")
    finally:
        db.close()

def start_scheduler():
    # Run Mon-Fri every 30 minutes between 7:00 AM and 6:00 PM (hour 7 to 18)
    trigger = CronTrigger(
        day_of_week='mon-fri',
        hour='7-18',
        minute='*/30',
        timezone='America/Caracas'
    )
    scheduler.add_job(
        run_consistency_check,
        trigger=trigger,
        args=[1, "System (Cron)"],
        id="consistency_cron",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started successfully (Cron: Mon-Fri, 7am-6pm, every 30m).")

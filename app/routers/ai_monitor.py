from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from .. import models, schemas
from app.dependencies import get_current_active_user, templates
import paramiko
import json
import requests

router = APIRouter(
    prefix="/ai_monitor",
    tags=["ai_monitor"]
)

@router.get("/", response_class=HTMLResponse)
async def view_ai_monitor(request: Request, user: models.User = Depends(get_current_active_user)):
    return templates.TemplateResponse("ai_monitor.html", {"request": request, "title": "Uso de IAs", "user": user})

@router.get("/api/stats")
def get_ai_stats(user: models.User = Depends(get_current_active_user)):
    stats = []
    tasks = []

    # 1. Fetch hardware stats via paramiko
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("192.168.1.79", 22, "administrador", "GRW7czL3*")

        # Get core count
        stdin_c, stdout_c, stderr_c = client.exec_command("nproc")
        try:
            cores = int(stdout_c.read().decode("utf-8").strip() or "1")
        except:
            cores = 1

        # Get docker stats
        cmd = "docker stats --no-stream --format '{{json .}}' luna_web autogen_studio ollama luna_bot"
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode("utf-8").strip()
        if out:
            for line in out.split('\n'):
                if line.strip():
                    data = json.loads(line)
                    cpu_raw = data.get("CPUPerc", "0%").replace("%", "")
                    try:
                        cpu_normalized = min(100.0, float(cpu_raw) / cores)
                    except:
                        cpu_normalized = 0.0

                    stats.append({
                        "name": data.get("Name", ""),
                        "cpu": f"{cpu_normalized:.2f}%",
                        "mem": data.get("MemUsage", "0"),
                        "mem_perc": data.get("MemPerc", "0%")
                    })
        client.close()
    except Exception as e:
        print("Error fetching docker stats:", e)

    # 2. Fetch active tasks
    try:
        r = requests.get("http://192.168.1.79:8099/api/monitor/tasks", verify=False, timeout=3)
        if r.status_code == 200:
            tasks = r.json().get("tasks", [])
    except Exception as e:
        print("Error fetching Luna tasks:", e)

    return {
        "status": "ok",
        "docker_stats": stats,
        "luna_tasks": tasks
    }

$TaskName = "ProfitPlus_SuperAuditor"
$ScriptPath = "$PSScriptRoot\super_workflow.py"
$PythonPath = (Get-Command python).Source
$TriggerTime = "08:00"

# Create the action
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument $ScriptPath -WorkingDirectory $PSScriptRoot

# Create the trigger (Weekly, Monday)
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At $TriggerTime

# Create the task
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Description "Ejecuta auditoria de inventario y calculo de compras (Profit Plus)" -Force

Write-Host "Tarea '$TaskName' programada exitosamente para los Lunes a las $TriggerTime"

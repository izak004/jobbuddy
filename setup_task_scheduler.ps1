# Registers a daily Windows Scheduled Task that runs the job-fetch pipeline.
# Run this once, from an ordinary PowerShell prompt in this folder:
#   powershell -ExecutionPolicy Bypass -File setup_task_scheduler.ps1
#
# It does NOT require admin rights (creates a task for the current user only).

$ErrorActionPreference = "Stop"
$projectDir = $PSScriptRoot
$batPath = Join-Path $projectDir "run_daily.bat"
$taskName = "JobBuddy-DailyFetch"

$action = New-ScheduledTaskAction -Execute $batPath -WorkingDirectory $projectDir
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Fetches new job postings daily for JobBuddy, based on your saved search criteria."

Write-Host "Scheduled task '$taskName' created. It will run daily at 8:00 AM."
Write-Host "If your laptop is off/asleep at that time, it runs at next login (StartWhenAvailable)."
Write-Host "To change the time: (Get-ScheduledTask -TaskName '$taskName' | Set-ScheduledTask -Trigger (New-ScheduledTaskTrigger -Daily -At 7:30AM))"

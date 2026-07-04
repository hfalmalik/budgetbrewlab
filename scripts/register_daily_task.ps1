# register_daily_task.ps1 — registers the Windows scheduled task "BrewLab Daily Article".
# Battery-safe, catches up via StartWhenAvailable (same pattern as the other empire tasks).
# Run:  powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $PSScriptRoot "new_article.ps1"
$TaskName = "BrewLab Daily Article"

$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`"" `
    -WorkingDirectory $Root

$Trigger = New-ScheduledTaskTrigger -Daily -At 10:30AM

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task '$TaskName'."
}

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "Generates one new BudgetBrewLab article via Claude Code and deploys to GitHub Pages." | Out-Null

Write-Host "Registered task '$TaskName' - runs daily at 10:30 AM."
Write-Host "Test it now with:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Logs land in:      $Root\scripts\logs\"

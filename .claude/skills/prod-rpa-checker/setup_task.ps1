# setup_task.ps1 - Register Windows Scheduled Task (run once)
# Usage: .\setup_task.ps1 -ProjectDir "e:\AI\pythonProject\aiAutoTest" -At "17:10"

param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectDir,

    [string]$At = "17:10",

    [string]$At2 = $null,

    [string]$TaskName = "RPA Data Check Daily",

    [string]$VenvDir = ".venv"
)

# Auto-locate skill directory (where this script lives)
$SkillDir = Split-Path $MyInvocation.MyCommand.Path -Parent
$RunCheck = Join-Path $SkillDir "run_check.py"

# Validate paths
if (-not (Test-Path $RunCheck)) {
    Write-Error "run_check.py not found: $RunCheck"
    exit 1
}
$envFile = Join-Path $ProjectDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Warning "WARNING: .env not found at $envFile. Please configure FEISHU_WEBHOOK_URL."
}

# Resolve venv python path (absolute, no PATH dependency)
$VenvPython = Join-Path $ProjectDir "$VenvDir\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment Python not found at: $VenvPython"
    exit 1
}

# ---------------------------------------------------------------------------
# Create a VBScript wrapper to ensure absolute zero window flashing
# and correct working directory
# ---------------------------------------------------------------------------
$LauncherVbs = Join-Path $SkillDir "run_check_silent.vbs"

# Escape double quotes for VBScript: " → ""
$EscapedProjectDir = $ProjectDir.Replace('"', '""')
$EscapedVenvPython = $VenvPython.Replace('"', '""')
$EscapedRunCheck = $RunCheck.Replace('"', '""')

$ExpectedVbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "$EscapedProjectDir"
WshShell.Run """$EscapedVenvPython"" """$EscapedRunCheck""", 0, True
"@

# Only generate VBS if it doesn't exist or content changed (avoid overwriting user edits)
if (-not (Test-Path $LauncherVbs)) {
    Set-Content -Path $LauncherVbs -Value $ExpectedVbsContent -Encoding Ascii
    Write-Host "  VBS     : Created $LauncherVbs"
} else {
    $ExistingVbsContent = Get-Content -Path $LauncherVbs -Raw -Encoding Ascii
    if ($ExistingVbsContent.Trim() -ne $ExpectedVbsContent.Trim()) {
        Set-Content -Path $LauncherVbs -Value $ExpectedVbsContent -Encoding Ascii
        Write-Host "  VBS     : Updated $LauncherVbs (paths changed)"
    } else {
        Write-Host "  VBS     : Up-to-date (skipped)"
    }
}

# Task Action: run wscript.exe to execute the VBScript silently
$action = New-ScheduledTaskAction `
    -Execute "wscript.exe" `
    -Argument "`"$LauncherVbs`"" `
    -WorkingDirectory $ProjectDir

$trigger1 = New-ScheduledTaskTrigger -Daily -At $At

if ($At2) {
    $trigger2 = New-ScheduledTaskTrigger -Daily -At $At2
    $triggers = @($trigger1, $trigger2)
    $triggerDescription = "Daily at $At and $At2"
} else {
    $triggers = @($trigger1)
    $triggerDescription = "Daily at $At"
}

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

# Principal: run whether user is logged on or not (required for WakeToRun to work without unlocking)
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $triggers `
    -Settings $settings `
    -Principal $principal `
    -Description "RPA data check at $triggerDescription, push result to Feishu group (Silent, wakes from sleep)" `
    -Force

Write-Host ""
Write-Host "[OK] Task registered: $TaskName (Silent Mode)"
Write-Host "  Triggers: $triggerDescription"
Write-Host "  Wrapper : wscript.exe -> run_check_silent.vbs"
Write-Host "  Command : $VenvPython $RunCheck"
Write-Host "  WorkDir : $ProjectDir"
Write-Host ""
Write-Host "To test manually:"
Write-Host "  Start-ScheduledTask -TaskName `"$TaskName`""

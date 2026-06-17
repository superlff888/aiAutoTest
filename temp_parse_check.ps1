$errs = $null
[System.Management.Automation.Language.Parser]::ParseFile('e:/AI/pythonProject/aiAutoTest/.claude/skills/prod-rpa-checker/setup_dual_task.ps1', [ref]$null, [ref]$errs) | Out-Null
$errs | ForEach-Object {
    Write-Host "Extent: $($_.Extent.StartLineNumber):$($_.Extent.StartColumnNumber) - $($_.Extent.EndLineNumber):$($_.Extent.EndColumnNumber)"
    Write-Host "Message: $($_.Message)"
    Write-Host "---"
}
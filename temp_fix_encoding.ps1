$src = 'e:/AI/pythonProject/aiAutoTest/.claude/skills/prod-rpa-checker/setup_dual_task.ps1'
# 用 UTF-8 with BOM 重新写一次
$content = Get-Content -Path $src -Raw -Encoding UTF8
[System.IO.File]::WriteAllText($src, $content, [System.Text.UTF8Encoding]::new($true))
Write-Host "Done: $($src)"
# 验证 BOM
$bytes = [System.IO.File]::ReadAllBytes($src) | Select-Object -First 3
Write-Host "First 3 bytes: $($bytes -join ',')"
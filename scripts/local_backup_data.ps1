$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $ProjectRoot "backend\data\local_save.sqlite3"
$BackupDir = Join-Path $ProjectRoot "backend\backups"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Target = Join-Path $BackupDir "local_save_$Timestamp.sqlite3"

if (-not (Test-Path $Source)) {
    Write-Error "未找到本地存档文件：$Source"
}

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
Copy-Item -Path $Source -Destination $Target -Force

Write-Host "本地存档已备份到：$Target"

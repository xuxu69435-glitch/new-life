$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $ProjectRoot "backend\data\local_save.sqlite3"
$BackupDir = Join-Path $ProjectRoot "backend\backups"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

Write-Host "此操作会重置本地 SQLite 存档。"
Write-Host "当前数据库：$Source"
$confirm = Read-Host "输入 YES 继续重置"

if ($confirm -ne "YES") {
    Write-Host "已取消。"
    exit 0
}

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

if (Test-Path $Source) {
    $BackupPath = Join-Path $BackupDir "local_save_before_reset_$Timestamp.sqlite3"
    Move-Item -Path $Source -Destination $BackupPath -Force
    Write-Host "原数据库已备份到：$BackupPath"
}

Write-Host "本地存档已重置。下次启动后端时会自动创建新的 SQLite 数据库。"

$ErrorActionPreference = "SilentlyContinue"

. (Join-Path $PSScriptRoot "_local_common.ps1")

Initialize-LocalRunDirectories

$runDir = Get-RunDir
$logDir = Get-LogDir
$sqlitePath = Get-SqliteDatabasePath
$latestBackup = Get-LatestBackupFile

$backendRunning = Test-ProjectBackendRunning
$frontendRunning = Test-ProjectFrontendRunning
$backendHealthy = if ($backendRunning) { Test-BackendHealth } else { $false }
$frontendReady = if ($frontendRunning) { Test-FrontendAccessible } else { $false }

Write-Host ""
Write-Host "=== 本地游戏状态 ==="
Write-Host ""
Write-Host "后端运行:$(if ($backendRunning) { '是' } else { '否' })"
Write-Host "前端运行:$(if ($frontendRunning) { '是' } else { '否' })"
Write-Host "后端 health:$(if ($backendHealthy) { '正常' } else { '不可用' })"
Write-Host "前端页面:$(if ($frontendReady) { '可访问' } else { '不可访问' })"
Write-Host ""
Write-Host "前端地址:$($script:LocalFrontendUrl)"
Write-Host "后端地址:$($script:LocalBackendUrl)"
Write-Host "后端 health:$($script:LocalHealthUrl)"
Write-Host ""
Write-Host "SQLite 存档:$sqlitePath"
if (Test-Path $sqlitePath) {
    $sizeKb = [math]::Round((Get-Item $sqlitePath).Length / 1KB, 2)
    Write-Host "SQLite 大小:$sizeKb KB"
}
else {
    Write-Host "SQLite 大小:文件不存在（首次启动后会自动创建）"
}

if ($latestBackup) {
    Write-Host "最近备份:$($latestBackup.FullName)"
}
else {
    Write-Host "最近备份:无"
}

Write-Host ""
Write-Host "本地日志目录:$logDir"
Write-Host "运行状态文件:$(Get-RunStatePath)"
Write-Host "后端 PID 文件:$(Join-Path $runDir 'backend.pid')"
Write-Host "前端 PID 文件:$(Join-Path $runDir 'frontend.pid')"
Write-Host ""

if (-not $backendHealthy -or -not $frontendReady) {
    Write-Host "提示:若服务未运行，请执行 scripts\start_game.ps1"
}

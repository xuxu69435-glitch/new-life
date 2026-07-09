$ErrorActionPreference = "SilentlyContinue"

. (Join-Path $PSScriptRoot "_local_common.ps1")

Initialize-LocalRunDirectories
Write-LauncherLog "local_stop.ps1 开始执行"

$runDir = Get-RunDir
$backendStopped = $false
$frontendStopped = $false

$backendPid = Get-PidFromFile (Join-Path $runDir "backend.pid")
$frontendPid = Get-PidFromFile (Join-Path $runDir "frontend.pid")

if (Stop-ProjectProcessByPid -ProcessId $backendPid -IsProjectProcess ${function:Test-IsProjectBackendProcess}) {
    $backendStopped = $true
    Write-LauncherLog "已停止记录的后端进程 PID=$backendPid"
}

if (Stop-ProjectProcessByPid -ProcessId $frontendPid -IsProjectProcess ${function:Test-IsProjectFrontendProcess}) {
    $frontendStopped = $true
    Write-LauncherLog "已停止记录的前端进程 PID=$frontendPid"
}

if (Stop-ProjectListenersOnPort -Port $script:LocalBackendPort -IsProjectProcess ${function:Test-IsProjectBackendProcess}) {
    $backendStopped = $true
    Write-LauncherLog "已停止监听 $($script:LocalBackendPort) 的本项目后端进程"
}

if (Stop-ProjectListenersOnPort -Port $script:LocalFrontendPort -IsProjectProcess ${function:Test-IsProjectFrontendProcess}) {
    $frontendStopped = $true
    Write-LauncherLog "已停止监听 $($script:LocalFrontendPort) 的本项目前端进程"
}

Remove-Item (Join-Path $runDir "backend.pid") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $runDir "frontend.pid") -Force -ErrorAction SilentlyContinue
Remove-Item (Get-RunStatePath) -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 1

$backendStillRunning = Test-ProjectBackendRunning
$frontendStillRunning = Test-ProjectFrontendRunning

Write-Host ""
if ($backendStopped -or -not $backendStillRunning) {
    Write-Host "后端已停止（端口 $($script:LocalBackendPort) 未被本项目占用）。"
}
else {
    Write-Host "警告:后端可能仍在运行，请检查日志:$(Join-Path (Get-LogDir) 'backend.log')"
}

if ($frontendStopped -or -not $frontendStillRunning) {
    Write-Host "前端已停止（端口 $($script:LocalFrontendPort) 未被本项目占用）。"
}
else {
    Write-Host "警告:前端可能仍在运行，请检查日志:$(Join-Path (Get-LogDir) 'frontend.log')"
}

Write-LauncherLog "local_stop.ps1 完成。backendRunning=$backendStillRunning frontendRunning=$frontendStillRunning"

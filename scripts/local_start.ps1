$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_local_common.ps1")

Initialize-LocalRunDirectories
Set-LocalEnvironment

$runDir = Get-RunDir
$logDir = Get-LogDir
$backendDir = Get-BackendDir
$frontendDir = Get-FrontendDir
$backendLog = Join-Path $logDir "backend.log"
$frontendLog = Join-Path $logDir "frontend.log"

Write-LauncherLog "local_start.ps1 开始执行"

$backendAlreadyRunning = Test-ProjectBackendRunning
$frontendAlreadyRunning = Test-ProjectFrontendRunning

if ($backendAlreadyRunning -and $frontendAlreadyRunning) {
    Write-Host "本项目前后端已在运行，无需重复启动。"
    Write-Host "前端页面:$($script:LocalFrontendUrl)"
    Write-Host "后端 health:$($script:LocalHealthUrl)"
    Write-LauncherLog "前后端已在运行，跳过启动"
    exit 2
}

$backendPid = 0
$frontendPid = 0

if ($backendAlreadyRunning) {
    Write-Host "后端已在运行，跳过启动。"
    $backendPid = Get-PidFromFile (Join-Path $runDir "backend.pid")
    if (-not (Test-ProcessAlive -ProcessId $backendPid)) {
        foreach ($pid in (Get-ListenerProcessIds -Port $script:LocalBackendPort)) {
            if (Test-IsProjectBackendProcess -ProcessId $pid) {
                $backendPid = $pid
                break
            }
        }
    }
}
else {
    if (Test-PortUsedByOtherProcess -Port $script:LocalBackendPort -IsProjectProcess ${function:Test-IsProjectBackendProcess}) {
        $message = "端口 $($script:LocalBackendPort) 已被其他程序占用，无法启动本项目后端。"
        Write-Host $message
        Write-LauncherLog $message
        exit 1
    }

    $backendProcess = Start-LoggedProcess `
        -FilePath "python" `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$($script:LocalBackendPort)") `
        -WorkingDirectory $backendDir `
        -LogFile $backendLog
    $backendPid = $backendProcess.Id
    $backendPid | Out-File -FilePath (Join-Path $runDir "backend.pid") -Encoding ascii -NoNewline
    Write-LauncherLog "已启动后端 PID=$backendPid"
}

if ($frontendAlreadyRunning) {
    Write-Host "前端已在运行，跳过启动。"
    $frontendPid = Get-PidFromFile (Join-Path $runDir "frontend.pid")
    if (-not (Test-ProcessAlive -ProcessId $frontendPid)) {
        foreach ($pid in (Get-ListenerProcessIds -Port $script:LocalFrontendPort)) {
            if (Test-IsProjectFrontendProcess -ProcessId $pid) {
                $frontendPid = $pid
                break
            }
        }
    }
}
else {
    if (Test-PortUsedByOtherProcess -Port $script:LocalFrontendPort -IsProjectProcess ${function:Test-IsProjectFrontendProcess}) {
        $message = "端口 $($script:LocalFrontendPort) 已被其他程序占用，无法启动本项目前端。"
        Write-Host $message
        Write-LauncherLog $message
        exit 1
    }

    $frontendProcess = Start-LoggedProcess `
        -FilePath "npm" `
        -ArgumentList @("run", "dev") `
        -WorkingDirectory $frontendDir `
        -LogFile $frontendLog
    $frontendPid = $frontendProcess.Id
    $frontendPid | Out-File -FilePath (Join-Path $runDir "frontend.pid") -Encoding ascii -NoNewline
    Write-LauncherLog "已启动前端 PID=$frontendPid"
}

Save-RunState -BackendPid $backendPid -FrontendPid $frontendPid

Write-Host ""
Write-Host "本地服务已启动。"
Write-Host "前端页面:$($script:LocalFrontendUrl)"
Write-Host "后端接口:$($script:LocalBackendUrl)"
Write-Host "后端 health:$($script:LocalHealthUrl)"
Write-Host "后端日志:$backendLog"
Write-Host "前端日志:$frontendLog"
Write-Host ""
Write-Host "推荐完整启动:scripts\start_game.ps1"
Write-Host "停止服务:scripts\local_stop.ps1"

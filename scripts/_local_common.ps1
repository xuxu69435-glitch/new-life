# Shared helpers for local game launcher scripts.

$script:LocalFrontendUrl = "http://127.0.0.1:1234"
$script:LocalBackendUrl = "http://127.0.0.1:4321"
$script:LocalHealthUrl = "http://127.0.0.1:4321/health"
$script:LocalBackendPort = 4321
$script:LocalFrontendPort = 1234

function Get-ProjectRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-RunDir {
    return Join-Path (Get-ProjectRoot) ".local-run"
}

function Get-LogDir {
    return Join-Path (Get-RunDir) "logs"
}

function Get-BackendDir {
    return Join-Path (Get-ProjectRoot) "backend"
}

function Get-FrontendDir {
    return Join-Path (Get-ProjectRoot) "frontend"
}

function Get-SqliteDatabasePath {
    return Join-Path (Get-BackendDir) "data\local_save.sqlite3"
}

function Get-BackupDir {
    return Join-Path (Get-BackendDir) "backups"
}

function Initialize-LocalRunDirectories {
    New-Item -ItemType Directory -Force -Path (Get-RunDir) | Out-Null
    New-Item -ItemType Directory -Force -Path (Get-LogDir) | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path (Get-BackendDir) "data") | Out-Null
}

function Write-LauncherLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    $logFile = Join-Path (Get-LogDir) "launcher.log"
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

function Set-LocalEnvironment {
    $env:ENVIRONMENT = "local"
    $env:SAVE_REPOSITORY_TYPE = "sqlite"
    $env:SQLITE_DATABASE_PATH = "data/local_save.sqlite3"
    $env:BACKEND_HOST = "127.0.0.1"
    $env:BACKEND_PORT = "$($script:LocalBackendPort)"
    $env:CORS_ALLOWED_ORIGINS = "http://127.0.0.1:1234,http://localhost:1234"
    $env:ENABLE_DEV_ROUTES = "true"
    $env:VITE_API_BASE_URL = $script:LocalBackendUrl
}

function Get-ProcessCommandLine {
    param([int]$ProcessId)
    if ($ProcessId -le 0) {
        return $null
    }
    try {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction Stop
        return $process.CommandLine
    }
    catch {
        return $null
    }
}

function Test-ProcessAlive {
    param([int]$ProcessId)
    if ($ProcessId -le 0) {
        return $false
    }
    return $null -ne (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

function Get-ListenerProcessIds {
    param([int]$Port)
    $ids = @()
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        if ($connection.OwningProcess -gt 0 -and $ids -notcontains $connection.OwningProcess) {
            $ids += [int]$connection.OwningProcess
        }
    }
    return $ids
}

function Test-IsProjectBackendProcess {
    param([int]$ProcessId)
    $commandLine = Get-ProcessCommandLine -ProcessId $ProcessId
    if (-not $commandLine) {
        return $false
    }
    return ($commandLine -match "uvicorn") -and ($commandLine -match "app\.main:app") -and ($commandLine -match "$($script:LocalBackendPort)")
}

function Test-IsProjectFrontendProcess {
    param([int]$ProcessId)
    $commandLine = Get-ProcessCommandLine -ProcessId $ProcessId
    if (-not $commandLine) {
        return $false
    }
    return ($commandLine -match "vite") -or (($commandLine -match "npm") -and ($commandLine -match "run dev"))
}

function Get-PidFromFile {
    param([string]$PidFile)
    if (-not (Test-Path $PidFile)) {
        return 0
    }
    $raw = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($raw -match '^\d+$') {
        return [int]$raw
    }
    return 0
}

function Get-RunStatePath {
    return Join-Path (Get-RunDir) "run-state.json"
}

function Save-RunState {
    param(
        [int]$BackendPid,
        [int]$FrontendPid
    )
    $state = [ordered]@{
        started_at = (Get-Date).ToString("o")
        backend_pid = $BackendPid
        frontend_pid = $FrontendPid
        backend_port = $script:LocalBackendPort
        frontend_port = $script:LocalFrontendPort
        frontend_url = $script:LocalFrontendUrl
        backend_url = $script:LocalBackendUrl
        health_url = $script:LocalHealthUrl
    }
    $state | ConvertTo-Json | Set-Content -Path (Get-RunStatePath) -Encoding UTF8
}

function Get-RunState {
    $path = Get-RunStatePath
    if (-not (Test-Path $path)) {
        return $null
    }
    try {
        return Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        return $null
    }
}

function Test-BackendHealth {
    try {
        $response = Invoke-WebRequest -Uri $script:LocalHealthUrl -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Test-FrontendAccessible {
    try {
        $response = Invoke-WebRequest -Uri $script:LocalFrontendUrl -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Wait-BackendHealth {
    param([int]$TimeoutSeconds = 60)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-BackendHealth) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Wait-FrontendAccessible {
    param([int]$TimeoutSeconds = 60)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-FrontendAccessible) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Test-ProjectBackendRunning {
    $runDir = Get-RunDir
    $recordedPid = Get-PidFromFile (Join-Path $runDir "backend.pid")
    if ((Test-ProcessAlive -ProcessId $recordedPid) -and (Test-IsProjectBackendProcess -ProcessId $recordedPid)) {
        return $true
    }
    foreach ($pid in (Get-ListenerProcessIds -Port $script:LocalBackendPort)) {
        if (Test-IsProjectBackendProcess -ProcessId $pid) {
            return $true
        }
    }
    return $false
}

function Test-ProjectFrontendRunning {
    $runDir = Get-RunDir
    $recordedPid = Get-PidFromFile (Join-Path $runDir "frontend.pid")
    if ((Test-ProcessAlive -ProcessId $recordedPid) -and (Test-IsProjectFrontendProcess -ProcessId $recordedPid)) {
        return $true
    }
    foreach ($pid in (Get-ListenerProcessIds -Port $script:LocalFrontendPort)) {
        if (Test-IsProjectFrontendProcess -ProcessId $pid) {
            return $true
        }
    }
    return $false
}

function Test-PortUsedByOtherProcess {
    param(
        [int]$Port,
        [scriptblock]$IsProjectProcess
    )
    foreach ($pid in (Get-ListenerProcessIds -Port $Port)) {
        if (-not (& $IsProjectProcess $pid)) {
            return $true
        }
    }
    return $false
}

function Start-LoggedProcess {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory,
        [string]$LogFile
    )
    $escapedArgs = ($ArgumentList | ForEach-Object {
        if ($_ -match '\s') { '"' + $_ + '"' } else { $_ }
    }) -join ' '
    $command = "$FilePath $escapedArgs >> `"$LogFile`" 2>&1"
    return Start-Process `
        -FilePath "cmd.exe" `
        -ArgumentList @("/c", $command) `
        -WorkingDirectory $WorkingDirectory `
        -PassThru `
        -WindowStyle Hidden
}

function Stop-ProjectProcessByPid {
    param(
        [int]$ProcessId,
        [scriptblock]$IsProjectProcess
    )
    if (-not (Test-ProcessAlive -ProcessId $ProcessId)) {
        return $false
    }
    if (& $IsProjectProcess $ProcessId) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
        return $true
    }
    return $false
}

function Stop-ProjectListenersOnPort {
    param(
        [int]$Port,
        [scriptblock]$IsProjectProcess
    )
    $stopped = $false
    foreach ($pid in (Get-ListenerProcessIds -Port $Port)) {
        if (& $IsProjectProcess $pid) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            $stopped = $true
        }
    }
    return $stopped
}

function Get-LatestBackupFile {
    $backupDir = Get-BackupDir
    if (-not (Test-Path $backupDir)) {
        return $null
    }
    return Get-ChildItem -Path $backupDir -Filter "*.sqlite3" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Open-GameBrowser {
    Start-Process $script:LocalFrontendUrl | Out-Null
}

$ErrorActionPreference = "SilentlyContinue"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RunDir = Join-Path $ProjectRoot ".local-run"

function Stop-ProcessByPort {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        if ($connection.OwningProcess -gt 0) {
            Stop-Process -Id $connection.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

function Stop-ProcessByPidFile {
    param([string]$PidFile)
    if (-not (Test-Path $PidFile)) {
        return
    }
    $processId = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($processId -match '^\d+$') {
        Stop-Process -Id ([int]$processId) -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

Stop-ProcessByPidFile (Join-Path $RunDir "backend.pid")
Stop-ProcessByPidFile (Join-Path $RunDir "frontend.pid")

Stop-ProcessByPort -Port 4321
Stop-ProcessByPort -Port 1234

Write-Host "已尝试停止本地后端(4321)和前端(1234)进程。"

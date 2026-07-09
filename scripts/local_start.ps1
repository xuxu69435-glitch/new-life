$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$RunDir = Join-Path $ProjectRoot ".local-run"

$env:ENVIRONMENT = "local"
$env:SAVE_REPOSITORY_TYPE = "sqlite"
$env:SQLITE_DATABASE_PATH = "data/local_save.sqlite3"
$env:BACKEND_HOST = "127.0.0.1"
$env:BACKEND_PORT = "4321"
$env:CORS_ALLOWED_ORIGINS = "http://127.0.0.1:1234,http://localhost:1234"
$env:ENABLE_DEV_ROUTES = "true"
$env:VITE_API_BASE_URL = "http://127.0.0.1:4321"

New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $BackendDir "data") | Out-Null

Push-Location $BackendDir
try {
    $backendProcess = Start-Process `
        -FilePath "python" `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "4321") `
        -PassThru `
        -WindowStyle Hidden
    $backendProcess.Id | Out-File -FilePath (Join-Path $RunDir "backend.pid") -Encoding ascii
}
finally {
    Pop-Location
}

Push-Location $FrontendDir
try {
    $frontendProcess = Start-Process `
        -FilePath "npm" `
        -ArgumentList @("run", "dev") `
        -PassThru `
        -WindowStyle Hidden
    $frontendProcess.Id | Out-File -FilePath (Join-Path $RunDir "frontend.pid") -Encoding ascii
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "本地服务已启动。"
Write-Host "前端页面：http://127.0.0.1:1234"
Write-Host "后端接口：http://127.0.0.1:4321"
Write-Host "后端health：http://127.0.0.1:4321/health"
Write-Host ""
Write-Host "停止服务请运行：scripts\local_stop.ps1"

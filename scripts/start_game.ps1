$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_local_common.ps1")

Initialize-LocalRunDirectories
Write-LauncherLog "start_game.ps1 开始执行"

$projectRoot = Get-ProjectRoot
$backendDir = Get-BackendDir
$frontendDir = Get-FrontendDir
$logDir = Get-LogDir

function Fail-Startup {
    param([string]$Message)
    Write-Host ""
    Write-Host "启动失败:$Message"
    Write-Host "排查建议:"
    Write-Host "- 查看启动日志:$(Join-Path $logDir 'launcher.log')"
    Write-Host "- 查看后端日志:$(Join-Path $logDir 'backend.log')"
    Write-Host "- 查看前端日志:$(Join-Path $logDir 'frontend.log')"
    Write-LauncherLog "启动失败:$Message"
    exit 1
}

if (-not (Test-Path (Join-Path $projectRoot "backend"))) {
    Fail-Startup "未找到 backend 目录，请在项目根目录运行本脚本。"
}

if (-not (Test-Path (Join-Path $projectRoot "frontend"))) {
    Fail-Startup "未找到 frontend 目录，请在项目根目录运行本脚本。"
}

try {
    $pythonVersion = (python --version 2>&1).ToString().Trim()
    Write-Host "Python:$pythonVersion"
    Write-LauncherLog "Python:$pythonVersion"
}
catch {
    Fail-Startup "未检测到 Python，请先安装 Python 3.11+ 并加入 PATH。"
}

try {
    $nodeVersion = (node --version 2>&1).ToString().Trim()
    Write-Host "Node:$nodeVersion"
    Write-LauncherLog "Node:$nodeVersion"
}
catch {
    Fail-Startup "未检测到 Node.js，请先安装 Node.js 并加入 PATH。"
}

try {
    $npmVersion = (npm --version 2>&1).ToString().Trim()
    Write-Host "npm:$npmVersion"
    Write-LauncherLog "npm:$npmVersion"
}
catch {
    Fail-Startup "未检测到 npm，请先安装 Node.js/npm。"
}

Push-Location $backendDir
try {
    python -c "import fastapi, uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "正在安装后端依赖..."
        Write-LauncherLog "开始安装后端依赖"
        pip install -e . | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Fail-Startup "后端依赖安装失败，请手动执行:cd backend; pip install -e ."
        }
    }
}
finally {
    Pop-Location
}

$nodeModules = Join-Path $frontendDir "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "未找到 frontend/node_modules，正在执行 npm install ..."
    Write-LauncherLog "开始执行 npm install"
    Push-Location $frontendDir
    try {
        npm install
        if ($LASTEXITCODE -ne 0) {
            Fail-Startup "前端依赖安装失败，请手动执行:cd frontend; npm install"
        }
    }
    finally {
        Pop-Location
    }
}

if (Test-ProjectBackendRunning -and (Test-ProjectFrontendRunning) -and (Test-BackendHealth) -and (Test-FrontendAccessible)) {
    Write-Host ""
    Write-Host "游戏已在运行，无需重复启动。"
    Write-Host "前端页面:$($script:LocalFrontendUrl)"
    Write-Host "后端 health:$($script:LocalHealthUrl)"
    Open-GameBrowser
    exit 0
}

$startScript = Join-Path $PSScriptRoot "local_start.ps1"
& $startScript
$startExitCode = $LASTEXITCODE
if ($startExitCode -eq 2) {
    Write-Host "检测到服务已在运行，继续等待健康检查..."
}
elseif ($startExitCode -ne 0) {
    Fail-Startup "local_start.ps1 返回错误码 $startExitCode"
}

Write-Host ""
Write-Host "等待后端 health（最多 60 秒）..."
if (-not (Wait-BackendHealth -TimeoutSeconds 60)) {
    Fail-Startup "后端 health 检查超时。请查看 $(Join-Path $logDir 'backend.log')"
}
Write-Host "后端 health 正常。"

Write-Host "等待前端页面（最多 60 秒）..."
if (-not (Wait-FrontendAccessible -TimeoutSeconds 60)) {
    Fail-Startup "前端页面访问超时。请查看 $(Join-Path $logDir 'frontend.log')"
}
Write-Host "前端页面可访问。"

Open-GameBrowser
Write-LauncherLog "启动成功，已打开浏览器"

Write-Host ""
Write-Host "游戏启动成功！"
Write-Host "前端页面:$($script:LocalFrontendUrl)"
Write-Host "后端 health:$($script:LocalHealthUrl)"
Write-Host "本地日志目录:$logDir"

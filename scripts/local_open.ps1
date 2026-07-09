$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_local_common.ps1")

if (-not (Test-BackendHealth)) {
    Write-Host "后端 health 当前不可用。"
    Write-Host "请先运行:powershell -ExecutionPolicy Bypass -File scripts\start_game.ps1"
    exit 1
}

Open-GameBrowser
Write-Host "已打开浏览器:$($script:LocalFrontendUrl)"
